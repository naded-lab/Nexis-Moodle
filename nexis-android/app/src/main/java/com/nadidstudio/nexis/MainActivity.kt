package com.nadidstudio.nexis

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.lifecycleScope
import com.nadidstudio.nexis.ui.navigation.NexisNavHost
import com.nadidstudio.nexis.ui.session.NexisSessionStore
import com.nadidstudio.nexis.ui.theme.NexisTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // Must be called before super.onCreate()/setContent() — this is what
        // paints the brand background+icon instantly at process start instead
        // of a blank white window, and hands off to Theme.Nexis the moment
        // the first Compose frame is ready (see Theme.Nexis.Splash).
        installSplashScreen()
        super.onCreate(savedInstanceState)

        // init() itself only sets up in-memory state — fast and safe to run
        // synchronously here. Anything that touches the Android Keystore
        // (encrypted API-key storage) is warmed up separately, off the main
        // thread, so it can never freeze the UI on first use.
        NexisSessionStore.init(applicationContext)
        lifecycleScope.launch { NexisSessionStore.warmUpSecureStorage() }

        enableEdgeToEdge()
        setContent {
            NexisTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    NexisNavHost()
                }
            }
        }
    }
}
