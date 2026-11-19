module App
  module Domain
    class Tier
      attr_reader :name, :percent_off

      def initialize(name, percent_off)
        @name = name
        @percent_off = percent_off
        freeze
      end

      STANDARD = new("standard", 0)
      SILVER = new("silver", 5)
      GOLD = new("gold", 10)
      SILVER_FROM_CENTS = 10_000
      GOLD_FROM_CENTS = 50_000
      private_constant :SILVER_FROM_CENTS, :GOLD_FROM_CENTS

      def self.for_subtotal(subtotal)
        return GOLD if subtotal.cents >= GOLD_FROM_CENTS
        return SILVER if subtotal.cents >= SILVER_FROM_CENTS

        STANDARD
      end
    end
  end
end
