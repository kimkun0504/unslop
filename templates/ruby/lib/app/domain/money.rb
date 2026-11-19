module App
  module Domain
    class Money
      CENTS_PER_UNIT = 100
      WHOLE_PERCENT = 100
      CANONICAL = /\A(?:0|[1-9][0-9]{0,11})\.[0-9]{2}\z/
      private_constant :CENTS_PER_UNIT, :WHOLE_PERCENT, :CANONICAL

      attr_reader :cents

      def self.zero
        new(0)
      end

      def self.parse(raw)
        trimmed = raw.strip
        canonical = trimmed.include?('.') ? trimmed : "#{trimmed}.00"
        raise(InvalidAmount.from(raw)) unless CANONICAL.match?(canonical)

        new(Integer(canonical.delete('.'), 10))
      end

      def initialize(cents)
        raise(ArgumentError, 'cents must be a non-negative Integer') unless cents.instance_of?(Integer) && !cents.negative?

        @cents = cents
        freeze
      end

      def plus(other)
        Money.new(cents + other.cents)
      end

      def less_percent(percent)
        Money.new((cents * (WHOLE_PERCENT - percent)).div(WHOLE_PERCENT))
      end

      def render
        units, rest = cents.divmod(CENTS_PER_UNIT)
        format('%<units>d.%<rest>02d', units:, rest:)
      end
    end
  end
end
