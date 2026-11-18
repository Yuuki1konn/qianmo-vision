plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val arm64Only = providers.gradleProperty("arm64Only")
    .map { it.equals("true", ignoreCase = true) }
    .orElse(false)

android {
    namespace = "com.qianmo.ruralvision"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.qianmo.ruralvision"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        if (arm64Only.get()) {
            ndk {
                abiFilters += listOf("arm64-v8a")
            }
        }

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
    }

    androidResources {
        noCompress += listOf("tflite", "onnx")
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.1")

    implementation("androidx.camera:camera-core:1.4.2")
    implementation("androidx.camera:camera-camera2:1.4.2")
    implementation("androidx.camera:camera-lifecycle:1.4.2")
    implementation("androidx.camera:camera-view:1.4.2")

    implementation("org.tensorflow:tensorflow-lite:2.17.0")
    implementation("org.tensorflow:tensorflow-lite-gpu-api:2.17.0")
    implementation("org.tensorflow:tensorflow-lite-gpu:2.17.0")
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.24.3")

    testImplementation("junit:junit:4.13.2")
}
