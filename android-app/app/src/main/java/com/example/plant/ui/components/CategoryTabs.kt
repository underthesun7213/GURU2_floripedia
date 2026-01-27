package com.example.plant.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.plant.data.model.FilterCategory

@Composable
fun FloripediaCategorySection(
    topCategories: List<String>,
    selectedTopIndex: Int,
    onTopCategoryClick: (Int) -> Unit,
    subCategories: List<FilterCategory>,
    onSubCategoryClick: (FilterCategory) -> Unit
) {
    val activeGreen = Color(0xFF4A6750)
    val inactiveGray = Color(0xFF636E72)

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFFF4F9F6))
            .padding(bottom = 16.dp)
    ) {
        TabRow(
            selectedTabIndex = selectedTopIndex,
            containerColor = Color.Transparent,
            contentColor = activeGreen,
            divider = {},
            indicator = { tabPositions ->
                if (selectedTopIndex < tabPositions.size) {
                    TabRowDefaults.SecondaryIndicator(
                        modifier = Modifier.tabIndicatorOffset(tabPositions[selectedTopIndex]),
                        height = 3.dp,
                        color = activeGreen
                    )
                }
            }
        ) {
            topCategories.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTopIndex == index,
                    onClick = { onTopCategoryClick(index) },
                    text = {
                        Text(
                            text = title,
                            fontSize = 13.sp,
                            fontWeight = if (selectedTopIndex == index) FontWeight.Bold else FontWeight.Medium,
                            color = if (selectedTopIndex == index) Color(0xFF2D3436) else inactiveGray,
                            maxLines = 1,
                            softWrap = false
                        )
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            subCategories.forEach { category ->
                Box(
                    modifier = Modifier.weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    SubCategoryItem(
                        category = category,
                        onClick = { onSubCategoryClick(category) },
                        activeColor = activeGreen
                    )
                }
            }
        }
    }
}

@Composable
fun SubCategoryItem(
    category: FilterCategory,
    onClick: () -> Unit,
    activeColor: Color
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clickable { onClick() }
            .padding(4.dp)
    ) {
        Box(
            modifier = Modifier
                .size(64.dp)
                .clip(CircleShape)
                .border(
                    width = if (category.isSelected) 3.dp else 0.dp,
                    color = activeColor,
                    shape = CircleShape
                )
        ) {
            Image(
                painter = painterResource(id = category.imageRes),
                contentDescription = category.name,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = category.name,
            fontSize = 13.sp,
            fontWeight = if (category.isSelected) FontWeight.Bold else FontWeight.Medium,
            color = if (category.isSelected) Color(0xFF2D3436) else Color(0xFF636E72)
        )
    }
}
