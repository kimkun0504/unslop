module App
  module Cli
    class Application
      EXIT_OK = 0
      EXIT_USAGE = 2
      USAGE = 'usage: app AMOUNT [AMOUNT ...]'.freeze
      public_constant :EXIT_OK, :EXIT_USAGE
      private_constant :USAGE

      def initialize(out, err)
        @out = out
        @err = err
        freeze
      end

      def run(arguments)
        return refuse(USAGE) if arguments.empty?

        quote = Domain::Quote.of(*arguments)
        @out.puts("subtotal=#{quote.subtotal.render} tier=#{quote.tier.name} total=#{quote.total.render}")
        EXIT_OK
      rescue Domain::InvalidAmount => e
        refuse(e.message)
      end

      private

      def refuse(message)
        @err.puts(message)
        EXIT_USAGE
      end
    end
  end
end
