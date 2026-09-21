#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"

# Adapts the hand-maintained prose specification snapshot to the compact
# instruction shape consumed by the AME artifact generators.
module ManualInstructionData
  MACHINE_READABLE_ROOT = Pathname.new(__FILE__).dirname.parent.expand_path
  INSTRUCTIONS_FILE = MACHINE_READABLE_ROOT / "manual-main/instructions.json"
  WAVEDROM_FIELD = /"bits":(\d+),"name":\s*("[^"]+"|0x[0-9a-f]+|\d+)/

  Variable = Struct.new(:name, :msb, :lsb) do
    def width = msb - lsb + 1
  end

  def self.load
    document = JSON.parse(INSTRUCTIONS_FILE.read)
    entries = document.fetch("instructions")
    names = entries.map { |entry| entry.fetch("name") }
    raise "duplicate manual instruction names: #{names.tally.select { |_name, count| count > 1 }.keys.join(', ')}" unless names.uniq.length == names.length

    entries.map do |entry|
      expected_mask = Integer(entry.fetch("mask"))
      expected_match = Integer(entry.fetch("match"))
      variables, mask, match = parse_encoding(entry.fetch("name"), entry.fetch("resolved_wavedrom"))
      unless mask == expected_mask && match == expected_match
        raise format("%s: WaveDrom mask/match %08x/%08x does not match snapshot %08x/%08x",
                     entry.fetch("name"), mask, match, expected_mask, expected_match)
      end

      assembly_text = assembly(entry)
      operands = assembly_text.split(",").map { |operand| operand.strip.delete("()") }.reject(&:empty?)
      unless operands == variables.map(&:name)
        raise "#{entry.fetch('name')}: mnemonic operands #{operands.join(', ')} do not match WaveDrom fields #{variables.map(&:name).join(', ')}"
      end

      {
        name: entry.fetch("name"),
        order: entry.fetch("order"),
        category: entry.fetch("category"),
        format: entry.fetch("format"),
        assembly: assembly_text,
        match: bit_pattern(expected_mask, expected_match),
        variables: variables,
        operation: entry.fetch("operation"),
        source_anchor: entry.fetch("anchor")
      }
    end.sort_by { |instruction| instruction.fetch(:order) }
  end

  def self.assembly(entry)
    entry.fetch("mnemonic").delete_prefix(entry.fetch("name")).strip
  end

  def self.parse_encoding(name, wavedrom)
    position = 0
    variables = []
    mask = 0
    match = 0
    wavedrom.scan(WAVEDROM_FIELD) do |width_text, token|
      width = width_text.to_i
      if token.start_with?("\"")
        variables << Variable.new(token[1...-1], position + width - 1, position)
      else
        value = Integer(token)
        raise "#{name}: encoding value #{token} does not fit #{width} bits" if value >= (1 << width)

        field_mask = ((1 << width) - 1) << position
        mask |= field_mask
        match |= value << position
      end
      position += width
    end

    raise "#{name}: WaveDrom encoding is #{position} bits, expected 32" unless position == 32
    [variables, mask, match]
  end

  def self.bit_pattern(mask, match)
    31.downto(0).map do |bit|
      ((mask >> bit) & 1).zero? ? "-" : ((match >> bit) & 1).to_s
    end.join
  end
end
