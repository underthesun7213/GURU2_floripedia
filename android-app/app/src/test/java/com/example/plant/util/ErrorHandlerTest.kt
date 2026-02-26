package com.example.plant.util

import org.junit.Assert.*
import org.junit.Test
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.io.IOException

class ErrorHandlerTest {

    // --- isAuthError ---

    @Test
    fun `401 메시지는 인증 에러`() {
        assertTrue(ErrorHandler.isAuthError(Exception("HTTP 401 Unauthorized")))
    }

    @Test
    fun `403 메시지는 인증 에러`() {
        assertTrue(ErrorHandler.isAuthError(Exception("HTTP 403 Forbidden")))
    }

    @Test
    fun `Unauthorized 문자열 인증 에러`() {
        assertTrue(ErrorHandler.isAuthError(Exception("Unauthorized access")))
    }

    @Test
    fun `404 메시지는 인증 에러 아님`() {
        assertFalse(ErrorHandler.isAuthError(Exception("HTTP 404 Not Found")))
    }

    @Test
    fun `null 메시지는 인증 에러 아님`() {
        assertFalse(ErrorHandler.isAuthError(Exception()))
    }

    // --- getErrorMessage ---

    @Test
    fun `SocketTimeoutException 시간 초과 메시지`() {
        val msg = ErrorHandler.getErrorMessage(SocketTimeoutException("timeout"))
        assertTrue(msg.contains("시간이 초과"))
    }

    @Test
    fun `UnknownHostException 인터넷 연결 메시지`() {
        val msg = ErrorHandler.getErrorMessage(UnknownHostException("no host"))
        assertTrue(msg.contains("인터넷 연결"))
    }

    @Test
    fun `IOException 네트워크 오류 메시지`() {
        val msg = ErrorHandler.getErrorMessage(IOException("io error"))
        assertTrue(msg.contains("네트워크 오류"))
    }

    @Test
    fun `500 에러 서버 오류 메시지`() {
        val msg = ErrorHandler.getErrorMessage(Exception("HTTP 500"))
        assertTrue(msg.contains("서버 오류"))
    }

    @Test
    fun `404 에러 찾을수없음 메시지`() {
        val msg = ErrorHandler.getErrorMessage(Exception("HTTP 404"))
        assertTrue(msg.contains("찾을 수 없습니다"))
    }

    @Test
    fun `알 수 없는 에러는 원본 메시지 반환`() {
        val msg = ErrorHandler.getErrorMessage(Exception("커스텀 에러"))
        assertEquals("커스텀 에러", msg)
    }
}
