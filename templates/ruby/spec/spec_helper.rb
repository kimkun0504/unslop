if ENV.fetch('COVERAGE', '') == '1'
  require 'simplecov'
  SimpleCov.start do
    enable_coverage :branch
    add_filter '/spec/'
    add_filter '/tools/'
    minimum_coverage line: 100, branch: 100
  end
end

module RaiseOnOwnWarnings
  LIB = File.expand_path('../lib', __dir__)
  private_constant :LIB

  def warn(message, ...)
    raise(message) if message.include?(LIB)

    super
  end
end

Warning[:deprecated] = true
Warning[:performance] = true
Warning.singleton_class.prepend(RaiseOnOwnWarnings)

require_relative '../lib/app'
require_relative 'support/recording_output'

RSpec.configure do |config|
  config.disable_monkey_patching!
  config.raise_errors_for_deprecations!
  config.fail_if_no_examples = true
  config.order = :random
  Kernel.srand(config.seed)
  config.expect_with(:rspec) { |expectations| expectations.syntax = :expect }
  config.mock_with(:rspec) { |mocks| mocks.verify_partial_doubles = true }
end
