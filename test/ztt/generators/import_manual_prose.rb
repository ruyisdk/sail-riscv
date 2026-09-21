#!/usr/bin/env ruby
# frozen_string_literal: true

# Import the normative instruction interface from the v0.6 prose manual.
#
# The AME specification no longer publishes the old UDB JSON snapshot.  This
# importer keeps our generator input structured while making the prose manual
# and its encoding-allocation registry the source of truth.

require "json"
require "optparse"
require "open3"
require "pathname"

ROOT = Pathname.new(__dir__).parent.expand_path
# The prose repository is a sibling of sail-ame in the workspace checkout.
DEFAULT_SOURCE = ROOT.parent.parent.parent / "riscv-attached-matrix-extension"
DEFAULT_OUTPUT = ROOT / "manual-main/instructions.json"

class ImportError < StandardError; end

class ProseImporter
  def initialize(source_root)
    @source = Pathname.new(source_root).expand_path
    @instructions_path = @source / "src/instructions.adoc"
    @allocation_path = @source / "scripts/data/instruction-encoding-allocation.json"
    raise ImportError, "manual source does not exist: #{@source}" unless @source.directory?
    raise ImportError, "missing #{@instructions_path}" unless @instructions_path.file?
    raise ImportError, "missing #{@allocation_path}" unless @allocation_path.file?
  end

  def import
    source = @instructions_path.read
    categories = parse_index(source)
    attributes = JSON.parse(@allocation_path.read).fetch("attributes")
    sections = source.scan(/^\[#([^\]]+)\]\n=== `([^`]+)`\n(.*?)(?=^\[#|\z)/m)
    raise ImportError, "no instruction sections found in #{@instructions_path}" if sections.empty?

    entries = sections.map.with_index do |(anchor, name, body), index|
      parse_instruction(anchor, name, body, index + 1, categories, attributes)
    end

    names = entries.map { |entry| entry.fetch("name") }
    duplicate_names = names.tally.select { |_name, count| count > 1 }.keys
    raise ImportError, "duplicate instruction names: #{duplicate_names.join(', ')}" unless duplicate_names.empty?

    commit = git("rev-parse", "HEAD")
    tag = git("describe", "--tags", "--exact-match", "HEAD", allow_failure: true)
    {
      "schema_version" => 2,
      "baseline_commit" => commit,
      "baseline_tag" => tag.empty? ? nil : tag,
      "source_repository" => "https://github.com/riscv/riscv-attached-matrix-extension.git",
      "source_path" => "src/instructions.adoc",
      "instructions" => entries
    }
  end

  private

  def parse_index(source)
    index = source.match(/^\[\[instruction-index\]\]\n(.*?)(?=^<<<)/m)&.[](1)
    raise ImportError, "missing instruction index" unless index
    category = nil
    categories = {}
    lines = index.lines
    lines.each_with_index do |line, line_index|
      if line.match?(/::\s*$/)
        header = line[/^([^|]+)::\s*$/, 1]
        raise ImportError, "unrecognized category header in instruction index: #{line.strip}" unless header
        category = header.strip
      elsif (match = line.match(/^a\| `([^`]+)`/)) &&
            (lines[line_index + 1].to_s.match(/^\| <<([^,>]+),([^>]+)>>/))
        mnemonic = match[1]
        name = mnemonic.split(/\s+/, 2).first
        raise ImportError, "instruction index lists #{name} before any category header" unless category
        categories[name] = category
      end
    end
    categories
  end

  def parse_instruction(anchor, name, body, order, categories, attributes)
    unless categories.key?(name)
      raise ImportError, "#{name}: documented instruction is missing from the instruction index"
    end

    mnemonic = required_field(body, "Mnemonic", name).match(/`([^`]+)`/)&.[](1)
    raise ImportError, "#{name}: malformed Mnemonic field" unless mnemonic
    diagram = body.match(/(\{"reg":\[.*?\]\})/m)&.[](1)
    raise ImportError, "#{name}: missing WaveDrom encoding" unless diagram

    resolved = resolve_wavedrom(name, diagram, attributes)
    mask, match = encoding_mask_match(name, resolved)
    {
      "order" => order,
      "name" => name,
      "anchor" => anchor,
      "category" => categories.fetch(name),
      "synopsis" => plain_text(required_field(body, "Synopsis", name)),
      "mnemonic" => mnemonic,
      "description" => prose_field(body, "Description", "Operation"),
      "operation" => operation(body, name),
      "wavedrom" => diagram,
      "resolved_wavedrom" => resolved,
      "format" => encoding_format(mask),
      "mask" => format("0x%08x", mask),
      "match" => format("0x%08x", match)
    }
  end

  def required_field(body, label, name)
    match = body.match(/^#{Regexp.escape(label)}::\n(.*?)(?=^(?:Synopsis|Mnemonic|Encoding|Description|Operation|Notes|See also)::|\z)/m)
    raise ImportError, "#{name}: missing #{label} field" unless match
    match[1]
  end

  def prose_field(body, start_label, end_label)
    match = body.match(/^#{Regexp.escape(start_label)}::\n(.*?)(?=^#{Regexp.escape(end_label)}::|\z)/m)
    plain_text(match ? match[1] : "")
  end

  def operation(body, name)
    match = body.match(/^Operation::\n(.*?)(?=^<<<|\z)/m)
    raise ImportError, "#{name}: missing Operation field" unless match
    code = match[1].match(/\n----\n(.*?)\n----/m)&.[](1)
    plain_text(code || match[1])
  end

  def plain_text(text)
    text.to_s.lines.map(&:rstrip)
      .reject { |line| line == "+" || line == "----" || line.start_with?("[source") }
      .join("\n")
      .strip
      .gsub(/\n{3,}/, "\n\n")
  end

  def resolve_wavedrom(name, diagram, attributes)
    fields = diagram.scan(/\{"bits"\s*:\s*(\d+)\s*,\s*"name"\s*:\s*(\{[^}]+\}|"[^"]+"|-?(?:0x[0-9a-f]+|\d+))\s*,\s*"type"\s*:\s*(-?\d+)\}/i)
    raise ImportError, "#{name}: malformed WaveDrom encoding" if fields.empty?
    encoded = fields.map do |bits, token, type|
      resolved_token = if token.start_with?("{")
        key = token[1...-1]
        value = attributes.fetch(key) { raise ImportError, "#{name}: unknown encoding attribute #{key}" }
        format("0x%x", Integer(value, 0))
      else
        token
      end
      %({"bits":#{bits.to_i},"name":#{resolved_token},"type":#{type.to_i}})
    end
    %({"reg":[#{encoded.join(',')}]})
  end

  def encoding_mask_match(name, resolved)
    position = 0
    mask = 0
    match = 0
    resolved.scan(/"bits":(\d+),"name":\s*("[^"]+"|0x[0-9a-f]+|-?\d+)/i) do |bits_text, token|
      bits = bits_text.to_i
      if token.start_with?("\"")
        # Operand field: the corresponding bits are variable.
      else
        value = Integer(token, 0)
        raise ImportError, "#{name}: encoding value #{token} does not fit #{bits} bits" if value.negative? || value >= (1 << bits)
        field_mask = ((1 << bits) - 1) << position
        mask |= field_mask
        match |= value << position
      end
      position += bits
    end
    raise ImportError, "#{name}: encoding is #{position} bits, expected 32" unless position == 32
    [mask, match]
  end

  def encoding_format(mask)
    dest = 0x00000f80
    src1 = 0x000f8000
    src2 = 0x01f00000
    return "R3" if (mask & src2) != src2
    return "R2" if (mask & src1) != src1
    return "R1" if (mask & dest) != dest
    "Fixed"
  end

  def git(*args, allow_failure: false)
    stdout, status = Open3.capture2("git", "-C", @source.to_s, *args)
    return "" if allow_failure && !status.success?
    raise ImportError, "git #{args.join(' ')} failed in #{@source}" unless status.success?
    stdout.strip
  end
end

options = { source: DEFAULT_SOURCE, output: DEFAULT_OUTPUT }
OptionParser.new do |parser|
  parser.banner = "Usage: #{File.basename($PROGRAM_NAME)} [options]"
  parser.on("--source PATH", "prose repository (default: #{DEFAULT_SOURCE})") { |path| options[:source] = path }
  parser.on("--output PATH", "JSON output (default: #{DEFAULT_OUTPUT})") { |path| options[:output] = path }
end.parse!

begin
  document = ProseImporter.new(options[:source]).import
  output = Pathname.new(options[:output]).expand_path
  output.dirname.mkpath
  output.write(JSON.pretty_generate(document) + "\n")
  puts "imported #{document.fetch('instructions').length} instructions from #{options[:source]}"
rescue ImportError, JSON::ParserError => error
  warn "manual prose import failed: #{error.message}"
  exit 1
end
