package com.example.plant.di

import com.example.plant.data.firebase.FirebaseAuthManager
import com.example.plant.data.firebase.FirebaseStorageManager
import com.example.plant.data.repository.AuthRepository
import com.example.plant.data.repository.PlantRepository
import com.example.plant.data.repository.UserRepository

/**
 * 앱 전역에서 사용할 의존성 컨테이너
 */
object AppContainer {

    val firebaseAuthManager: FirebaseAuthManager by lazy {
        FirebaseAuthManager()
    }

    val firebaseStorageManager: FirebaseStorageManager by lazy {
        FirebaseStorageManager()
    }

    val authRepository: AuthRepository by lazy {
        AuthRepository()
    }

    val plantRepository: PlantRepository by lazy {
        PlantRepository()
    }

    val userRepository: UserRepository by lazy {
        UserRepository()
    }
}
