package com.example.plant.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.plant.R

@Composable
fun FloripediaBottomBar(
    selectedMenu: String = "home",
    onNavigate: (String) -> Unit = {},
    onCameraClick: () -> Unit = {}
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .wrapContentHeight(),
        contentAlignment = Alignment.BottomCenter
    ) {
        // 하단 바 배경 (흰색)
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp),
            color = Color.White,
            shadowElevation = 8.dp
        ) {
            Row(
                modifier = Modifier.fillMaxSize(),
                horizontalArrangement = Arrangement.SpaceAround,
                verticalAlignment = Alignment.CenterVertically
            ) {
                BottomNavItem(
                    label = "홈",
                    drawableRes = if (selectedMenu == "home") R.drawable.round_home_24 else R.drawable.outline_home_24,
                    isSelected = selectedMenu == "home",
                    onClick = { onNavigate("home") }
                )
                BottomNavItem(
                    label = "탐색",
                    drawableRes = R.drawable.round_search_24,
                    isSelected = selectedMenu == "search",
                    onClick = { onNavigate("search") }
                )

                // 중앙 카메라 버튼 자리 비우기
                Spacer(modifier = Modifier.width(72.dp))

                BottomNavItem(
                    label = "꽃갈피",
                    drawableRes = R.drawable.baseline_bookmark_border_24,
                    isSelected = selectedMenu == "bookmark",
                    onClick = { onNavigate("bookmark") }
                )
                BottomNavItem(
                    label = "마이",
                    drawableRes = R.drawable.outline_person_24,
                    isSelected = selectedMenu == "my",
                    onClick = { onNavigate("my") }
                )
            }
        }

        // 카메라 FAB (70% 정도 겹치게 배치)
        FloatingActionButton(
            onClick = onCameraClick,
            modifier = Modifier
                .size(72.dp)
                .offset(y = (-12).dp),
            containerColor = Color(0xFF4A6750),
            contentColor = Color.White,
            shape = CircleShape,
            elevation = FloatingActionButtonDefaults.elevation(8.dp)
        ) {
            Icon(
                painter = painterResource(id = R.drawable.baseline_camera_alt_40),
                contentDescription = "Camera",
                modifier = Modifier.size(36.dp)
            )
        }
    }
}

@Composable
fun RowScope.BottomNavItem(
    label: String,
    drawableRes: Int,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val activeColor = Color(0xFF4A6750)
    val inactiveColor = Color(0xFF636E72)
    val indicatorColor = Color(0xFFE8F5E9)

    Column(
        modifier = Modifier
            .weight(1f)
            .fillMaxHeight(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.height(32.dp)
        ) {
            if (isSelected) {
                // 선택 시 연초록 원형 배경
                Surface(
                    modifier = Modifier.size(width = 44.dp, height = 32.dp),
                    shape = CircleShape,
                    color = indicatorColor
                ) {}
            }
            
            IconButton(onClick = onClick) {
                Icon(
                    painter = painterResource(id = drawableRes),
                    contentDescription = label,
                    tint = if (isSelected) activeColor else inactiveColor,
                    modifier = Modifier.size(24.dp)
                )
            }
        }
        
        Text(
            text = label,
            fontSize = 11.sp,
            color = if (isSelected) activeColor else inactiveColor,
            modifier = Modifier.padding(top = 2.dp)
        )
    }
}
