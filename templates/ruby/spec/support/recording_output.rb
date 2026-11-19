class RecordingOutput
  attr_reader :lines

  def initialize
    @lines = []
  end

  def puts(line)
    @lines << line
    nil
  end
end
