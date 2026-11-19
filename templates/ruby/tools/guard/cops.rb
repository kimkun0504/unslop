require "rubocop"

module RuboCop
  module Cop
    module Guard
      class OutputThroughPort < Base
        MSG = "write through an Output port; the process streams belong to bin/"
        WRITERS = %i[puts print p pp printf putc warn display].freeze
        GLOBALS = %i[$stdout $stderr $stdin].freeze
        STREAMS = %i[STDOUT STDERR STDIN].freeze

        def on_send(node)
          add_offense(node) if node.receiver.nil? && WRITERS.include?(node.method_name)
        end

        def on_gvar(node)
          add_offense(node) if GLOBALS.include?(node.children.first)
        end

        def on_const(node)
          add_offense(node) if top_level?(node) && STREAMS.include?(node.short_name)
        end

        private

        def top_level?(node)
          node.namespace.nil? || node.namespace.cbase_type?
        end
      end

      class DomainPurity < Base
        IO_MSG = "the domain does no I/O: move %<name>s behind a port in App::Cli"
        LAYER_MSG = "App::Domain must not depend on App::Cli"
        IO_CONSTANTS = %i[File IO Dir Pathname FileUtils Net Socket TCPSocket UDPSocket ENV Process Open3 Kernel
                          Time Random SecureRandom].freeze
        IO_CALLS = %i[system exec spawn fork open gets readline readlines sleep rand srand require
                      require_relative load exit exit! abort at_exit].freeze

        def on_const(node)
          name = node.short_name
          add_offense(node, message: LAYER_MSG) if name == :Cli
          add_offense(node, message: format(IO_MSG, name:)) if top_level?(node) && IO_CONSTANTS.include?(name)
        end

        def on_send(node)
          return unless node.receiver.nil? && IO_CALLS.include?(node.method_name)

          add_offense(node, message: format(IO_MSG, name: node.method_name))
        end

        def on_xstr(node)
          add_offense(node, message: format(IO_MSG, name: "a shell command"))
        end

        private

        def top_level?(node)
          node.namespace.nil? || node.namespace.cbase_type?
        end
      end
    end
  end
end
