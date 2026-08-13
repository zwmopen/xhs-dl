package com.zwmopen.xhsdl;

import static org.junit.Assert.assertThrows;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Arrays;

import org.junit.Test;

public final class MediaSaverTest {
    @Test
    public void rejectsTinyPassthroughResponses() throws Exception {
        Method method = writeContentMethod();
        byte[] tiny = new byte[199];
        InvocationTargetException error = assertThrows(
                InvocationTargetException.class,
                () -> method.invoke(null, new ByteArrayInputStream(tiny),
                        new ByteArrayOutputStream(), "keep", "video/mp4"));
        org.junit.Assert.assertTrue(error.getCause() instanceof java.io.IOException);
    }

    @Test
    public void acceptsNormalPassthroughResponses() throws Exception {
        Method method = writeContentMethod();
        byte[] media = new byte[200];
        Arrays.fill(media, (byte) 7);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        method.invoke(null, new ByteArrayInputStream(media), output, "keep", "video/mp4");
        org.junit.Assert.assertArrayEquals(media, output.toByteArray());
    }

    private static Method writeContentMethod() throws NoSuchMethodException {
        Method method = MediaSaver.class.getDeclaredMethod(
                "writeContent", java.io.InputStream.class, java.io.OutputStream.class,
                String.class, String.class);
        method.setAccessible(true);
        return method;
    }
}
