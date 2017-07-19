/*
 *  Serialization based implementation of mbedtls_* filesystem IO functions.
 *
 *  Copyright (C) 2017, ARM Limited, All Rights Reserved
 *  SPDX-License-Identifier: Apache-2.0
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may
 *  not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *  This file is part of mbed TLS (https://tls.mbed.org)
 */

#include "mbedtls/fsio.h"


#if defined(MBEDTLS_FS_IO) && defined(MBEDTLS_FS_IO_ALT)

/**
 * \brief          Open file. Follows standard C fopen interface.
 *
 * \param path     File path
 * \param mode     Open mode
 *
 * \return         Pointer to mbedtls_file_t on success or NULL on failure.
 */
mbedtls_file_t * mbedtls_fopen( const char *path, const char *mode )
{
    mbedtls_serialize_push_start();
    mbedtls_serialize_push_int16( MBEDTLS_SERIALIZE_FS_IO_TAG_FOPEN );
    mbedtls_serialize_push_buffer( path, strlen( path_len ) );
    mbedtls_serialize_push_buffer( mode, strlen( mode ) );
    mbedtls_serialize_push_end();

    mbedtls_serialize_pop_start();
    mbedtls_serialize_pop_int32( ); /* Status */
    mbedtls_serialize_pop_int32( ); /* Id */
    mbedtls_serialize_pop_int32( ); /* length */
    mbedtls_serialize_pop_end();
    return NULL;
}

/**
 * \brief          Read file. Follows standard C fread interface.
 *
 * \param ptr      Pointer to output buffer
 * \param size     Size of read items.
 * \param nmemb    Number of read items.
 * \param stream   Pointer to mbedtls_file_t.
 *
 * \return         Number of items read.
 */
size_t mbedtls_fread( void *ptr, size_t size, size_t nmemb,
                      mbedtls_file_t *stream )
{
    return 0;
}

/**
 * \brief          Write file. Follows standard C fwrite interface.
 *
 * \param ptr      Pointer to input buffer
 * \param size     Size of write items.
 * \param nmemb    Number of write items.
 * \param stream   Pointer to mbedtls_file_t.
 *
 * \return         Number of items written.
 */
size_t mbedtls_fwrite( const void *ptr, size_t size, size_t nmemb,
                       mbedtls_file_t *stream )
{
    return 0;
}

/**
 * \brief          Reads a line from file. Follows standard C fgets interface.
 *
 * \param s        Pointer to output buffer.
 * \param size     Size of buffer.
 * \param stream   Pointer to mbedtls_file_t.
 *
 * \return         returns s on success, and NULL on error or
 *                 when end of file occurs while no characters have been read.
 */
char * mbedtls_fgets( char *s, int size, mbedtls_file_t *stream )
{
    return NULL;
}

/**
 * \brief          Sets file position. Follows standard C fseek interface.
 *
 * \param stream   Pointer to mbedtls_file_t.
 * \param offset   Offset from whence.
 * \param whence   Position from where offset is applied.
 *                 Value is one of MBEDTLS_SEEK_SET, MBEDTLS_SEEK_CUR, or MBEDTLS_SEEK_END.
 *
 * \return         returns 0 on success, and -1 on error
 */
int mbedtls_fseek( mbedtls_file_t *stream, long offset, int whence )
{
    return 0;
}

/**
 * \brief          Gives current position of file in bytes.
 *                 Follows standard C ftell interface.
 *
 * \param stream   Pointer to mbedtls_file_t.
 *
 * \return         returns current position on success, and -1 on error
 */
long mbedtls_ftell( mbedtls_file_t *stream )
{
    return 0;
}

/**
 * \brief          Close file. Follows standard C fread interface.
 *
 * \param stream   Pointer to mbedtls_file_t.
 *
 * \return         Pointer to mbedtls_file_t on success or NULL on failure.
 */
int mbedtls_fclose( mbedtls_file_t *stream )
{
    return -1;
}

/**
 * \brief          Test error indicator. Follows standard C ferror interface.
 *
 * \param stream   Pointer to mbedtls_file_t.
 *
 * \return         Non zero error code if error is set. 0 for no error.
 */
int mbedtls_ferror( mbedtls_file_t *stream )
{
    return 0;
}

#endif /* MBEDTLS_FS_IO && MBEDTLS_FS_IO_ALT */
