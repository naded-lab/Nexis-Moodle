package com.nadidstudio.nexis.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.nadidstudio.nexis.ui.screens.shell.NexisShell
import com.nadidstudio.nexis.ui.screens.splash.NexisSplashScreen

object NexisRoutes {
    const val SPLASH = "splash"
    const val SHELL = "shell"
}

@Composable
fun NexisNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = NexisRoutes.SPLASH) {
        composable(NexisRoutes.SPLASH) {
            NexisSplashScreen(
                onFinished = {
                    navController.navigate(NexisRoutes.SHELL) {
                        popUpTo(NexisRoutes.SPLASH) { inclusive = true }
                    }
                }
            )
        }

        composable(NexisRoutes.SHELL) {
            NexisShell()
        }
    }
}
