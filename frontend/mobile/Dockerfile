# Dockerfile for building and running Svelte Native (NativeScript) Android apps
# Combines Node.js, NativeScript CLI, and Android SDK (mounted at runtime)

FROM thyrlian/android-sdk:latest

# Install Node.js (LTS) and npm
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    npm install -g nativescript && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables for NativeScript Android builds
ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH=$PATH:/opt/android-sdk/emulator:/opt/android-sdk/tools:/opt/android-sdk/tools/bin:/opt/android-sdk/platform-tools:$JAVA_HOME/bin

# Set working directory
WORKDIR /workspace

# Default command: bash (so you can run npm/ns commands interactively)
CMD ["bash"]
