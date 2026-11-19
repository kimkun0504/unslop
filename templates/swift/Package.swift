// swift-tools-version: 6.2
import PackageDescription

let strict: [SwiftSetting] = [
    .treatAllWarnings(as: .error),
    .enableUpcomingFeature("ExistentialAny"),
    .enableUpcomingFeature("InternalImportsByDefault"),
    .enableUpcomingFeature("MemberImportVisibility"),
    .strictMemorySafety(),
]

let package = Package(
    name: "App",
    targets: [
        .target(name: "Domain", swiftSettings: strict),
        .target(name: "CLI", dependencies: ["Domain"], swiftSettings: strict),
        .executableTarget(name: "app", dependencies: ["CLI"], swiftSettings: strict),
        .testTarget(name: "DomainTests", dependencies: ["Domain"], swiftSettings: strict),
        .testTarget(name: "CLITests", dependencies: ["CLI"], swiftSettings: strict),
    ]
)
