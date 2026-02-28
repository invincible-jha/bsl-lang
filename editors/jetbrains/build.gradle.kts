import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    id("java")
    id("org.jetbrains.kotlin.jvm") version "1.9.22"
    id("org.jetbrains.intellij") version "1.17.0"
}

group = "com.aumos.bsl"
version = providers.gradleProperty("pluginVersion").get()

repositories {
    mavenCentral()
}

// IntelliJ Platform Plugin configuration
intellij {
    version.set(providers.gradleProperty("platformVersion").get())
    type.set("IC")  // IntelliJ Community Edition — also covers PyCharm, WebStorm etc.
    plugins.set(listOf<String>())
    downloadSources.set(true)
    updateSinceUntilBuild.set(true)
}

tasks {
    // Set JVM compatibility
    withType<JavaCompile> {
        sourceCompatibility = "17"
        targetCompatibility = "17"
    }

    withType<KotlinCompile> {
        kotlinOptions.jvmTarget = "17"
    }

    patchPluginXml {
        sinceBuild.set(providers.gradleProperty("pluginSinceBuild").get())
        untilBuild.set(providers.gradleProperty("pluginUntilBuild").get())
    }

    signPlugin {
        certificateChain.set(System.getenv("CERTIFICATE_CHAIN") ?: "")
        privateKey.set(System.getenv("PRIVATE_KEY") ?: "")
        password.set(System.getenv("PRIVATE_KEY_PASSWORD") ?: "")
    }

    publishPlugin {
        token.set(System.getenv("PUBLISH_TOKEN") ?: "")
    }

    buildSearchableOptions {
        // Disabled to speed up local builds; enable before publishing
        enabled = false
    }
}
