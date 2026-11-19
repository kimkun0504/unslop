module App
  module Domain
    class InvalidAmount < ArgumentError
      def self.from(raw)
        new(%(expected a non-negative amount like 12 or 12.50, got "#{raw}"))
      end
    end
  end
end
