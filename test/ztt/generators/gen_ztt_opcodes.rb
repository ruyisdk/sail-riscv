#!/usr/bin/env ruby
# frozen_string_literal: true

# Generate a riscv-opcodes-style file for Ztt from the current prose
# specification instruction snapshot.
#
# Usage:
#   ruby generators/gen_ztt_opcodes.rb
#   ruby generators/gen_ztt_opcodes.rb --output-dir path/to/output
#   ruby generators/gen_ztt_opcodes.rb --stdout

require "fileutils"
require "optparse"
require "pathname"
require "tempfile"
require_relative "manual_instruction_data"

MACHINE_READABLE_ROOT = Pathname.new(__FILE__).dirname.parent.expand_path
DEFAULT_OUTPUT_DIR = MACHINE_READABLE_ROOT / "generated"

FixedField = Struct.new(:msb, :lsb, :value)
Variable = ManualInstructionData::Variable

def assembly_operands(assembly)
  assembly.to_s.split(",").map { |operand| operand.strip.delete("()") }.reject(&:empty?)
end

def load_instructions
  ManualInstructionData.load.map do |instruction|
    instruction.merge(pseudos: [])
  end
end

def write_atomically(path, text)
  path = Pathname.new(path)
  FileUtils.mkdir_p(path.dirname)
  Tempfile.create([".#{path.basename}.", ".tmp"], path.dirname.to_s) do |temporary|
    temporary.write(text)
    temporary.flush
    temporary.fsync
    File.rename(temporary.path, path.to_s)
  end
end

def ordered_variables(inst)
  by_name = inst[:variables].to_h { |var| [var.name, var] }
  seen = {}
  ordered = assembly_operands(inst[:assembly]).filter_map do |operand|
    var = by_name[operand]
    seen[operand] = true if var
    var
  end
  ordered + inst[:variables].reject { |var| seen[var.name] }
end

def fixed_fields(match)
  fields = []
  bit = 31
  while bit >= 0
    char = match[31 - bit]
    if char == "-"
      bit -= 1
      next
    end

    msb = bit
    bits = +""
    while bit >= 0 && match[31 - bit] != "-"
      bits << match[31 - bit]
      bit -= 1
    end
    fields << FixedField.new(msb, bit + 1, bits.to_i(2))
  end
  fields
end

def fixed_fields_without_variables(inst)
  variable_bits = {}
  inst[:variables].each { |var| (var.lsb..var.msb).each { |bit| variable_bits[bit] = true } }

  fixed_fields(inst[:match]).flat_map do |field|
    result = []
    bit = field.msb
    while bit >= field.lsb
      if variable_bits[bit]
        bit -= 1
        next
      end

      msb = bit
      value = 0
      while bit >= field.lsb && !variable_bits[bit]
        value = (value << 1) | ((field.value >> (bit - field.lsb)) & 1)
        bit -= 1
      end
      result << FixedField.new(msb, bit + 1, value)
    end
    result
  end
end

def fixed_token(field)
  return "#{field.msb}=#{field.value}" if field.msb == field.lsb

  "#{field.msb}..#{field.lsb}=0x#{field.value.to_s(16)}"
end

def read_arg_lut(path)
  return {} unless path

  path = Pathname.new(path).expand_path
  abort "Argument lookup table does not exist: #{path}" unless path.file?

  path.each_line.each_with_object({}) do |line, lut|
    match = line.strip.match(/\A"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)\z/)
    lut[match[1]] = [match[2].to_i, match[3].to_i] if match
  end
end

def variable_positions(instructions)
  instructions.each_with_object(Hash.new { |h, k| h[k] = [] }) do |inst, positions|
    inst[:variables].each do |var|
      pos = [var.msb, var.lsb]
      positions[var.name] << pos unless positions[var.name].include?(pos)
    end
  end
end

def variable_token(var, positions, arg_lut)
  pos = [var.msb, var.lsb]
  if positions[var.name].size == 1 && [nil, pos].include?(arg_lut[var.name])
    [var.name, [var.name, var.msb, var.lsb]]
  else
    field_name = "#{var.name}_#{var.msb}_#{var.lsb}"
    ["#{field_name}=#{var.name}", [field_name, var.msb, var.lsb]]
  end
end

def pseudo_lines(inst, positions, arg_lut)
  by_name = inst[:variables].to_h { |var| [var.name, var] }
  lines = []
  required = []

  inst[:pseudos].each do |pseudo|
    next unless pseudo["when"].to_s.include?("==")

    condition_name, condition_value = pseudo["when"].split("==", 2).map(&:strip)
    condition_var = by_name[condition_name]
    next unless condition_var

    pseudo_name, pseudo_args = pseudo["to"].split(/\s+/, 2)
    operands = assembly_operands(pseudo_args).filter_map do |operand|
      var = by_name[operand]
      next unless var

      token, lut = variable_token(var, positions, arg_lut)
      required << lut
      token
    end

    encoded_value = condition_value.to_i & ((1 << condition_var.width) - 1)
    forced = fixed_token(FixedField.new(condition_var.msb, condition_var.lsb, encoded_value))
    fixed = fixed_fields_without_variables(inst).map { |field| fixed_token(field) }
    lines << ["$pseudo_op", "rv_ztt::#{inst[:name]}", pseudo_name, *operands, forced, *fixed].join(" ")
  end

  [lines, required]
end

stdout = false
output_dir = DEFAULT_OUTPUT_DIR
output_basename = "rv_ztt"
arg_lut_path = ENV["RISCV_OPCODES_ARG_LUT"]
OptionParser.new do |opts|
  opts.banner = "Usage: ruby generators/gen_ztt_opcodes.rb [--output-dir DIRECTORY] [--output-basename NAME] [--arg-lut FILE] [--stdout]"
  opts.on("--output-dir DIRECTORY", "Write generated files to DIRECTORY instead of generated") do |path|
    output_dir = Pathname.new(path).expand_path
  end
  opts.on("--arg-lut FILE", "Read an existing riscv-opcodes arg_lut.csv (default: RISCV_OPCODES_ARG_LUT)") do |path|
    arg_lut_path = path
  end
  opts.on("--output-basename NAME", "Write NAME and NAME_arg_lut.csv instead of rv_ztt artifacts") do |name|
    output_basename = name
  end
  opts.on("--stdout", "Write rv_ztt to stdout instead of generated/rv_ztt") { stdout = true }
end.parse!

if output_basename.empty? || output_basename != File.basename(output_basename)
  abort "Output basename must be a non-empty file name: #{output_basename.inspect}"
end

instructions = load_instructions
arg_lut = read_arg_lut(arg_lut_path)
positions = variable_positions(instructions)
required_lut = []

lines = [
  "# This file is generated by generators/gen_ztt_opcodes.rb.",
  "# Source: manual-main/instructions.json",
  "# Do not edit by hand.",
  ""
]

instructions.each do |inst|
  operands = ordered_variables(inst).map do |var|
    token, lut = variable_token(var, positions, arg_lut)
    required_lut << lut
    token
  end
  fixed = fixed_fields_without_variables(inst).map { |field| fixed_token(field) }
  lines << [inst[:name], *operands, *fixed].join(" ")

  pseudos, pseudo_lut = pseudo_lines(inst, positions, arg_lut)
  lines.concat(pseudos)
  required_lut.concat(pseudo_lut)
  lines << ""
end

opcodes_text = lines.join("\n").rstrip + "\n"

if stdout
  print opcodes_text
else
  write_atomically(output_dir / output_basename, opcodes_text)
  write_atomically(
    output_dir / "#{output_basename}_arg_lut.csv",
    "# AME operand fields for riscv-opcodes/arg_lut.csv.\n" +
      required_lut.uniq.sort.map { |name, msb, lsb| %("#{name}", #{msb}, #{lsb}) }.join("\n") +
      "\n"
  )
end
