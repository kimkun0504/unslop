module App
  module Domain
    class Quote
      attr_reader :subtotal, :tier, :total

      def self.of(*lines)
        subtotal = lines.reduce(Money.zero) { |sum, line| sum.plus(Money.parse(line)) }
        tier = Tier.for_subtotal(subtotal)
        new(subtotal, tier, subtotal.less_percent(tier.percent_off))
      end

      def initialize(subtotal, tier, total)
        @subtotal = subtotal
        @tier = tier
        @total = total
        freeze
      end
    end
  end
end
