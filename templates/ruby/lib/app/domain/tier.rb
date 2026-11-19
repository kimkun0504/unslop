module App
  module Domain
    Tier = Data.define(:name, :percent_off)

    class Tier
      STANDARD = new(name: 'standard', percent_off: 0)
      SILVER = new(name: 'silver', percent_off: 5)
      GOLD = new(name: 'gold', percent_off: 10)
      SILVER_FROM_CENTS = 10_000
      GOLD_FROM_CENTS = 50_000
      public_constant :STANDARD, :SILVER, :GOLD
      private_constant :SILVER_FROM_CENTS, :GOLD_FROM_CENTS

      def self.for_subtotal(subtotal)
        return GOLD if subtotal.cents >= GOLD_FROM_CENTS
        return SILVER if subtotal.cents >= SILVER_FROM_CENTS

        STANDARD
      end
    end
  end
end
