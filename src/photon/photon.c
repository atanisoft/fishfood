/* Copyright 2023 Winterbloom LLC & Alethea Katherine Flowers

Use of this source code is governed by an MIT-style
license that can be found in the LICENSE.md file or at
https://opensource.org/licenses/MIT. */


#include <stdint.h>

#include "pico/time.h"
#include "report.h"
#include "config/serial.h"

#if HAS_RS485 && USE_PHOTON_FEEDERS

#define READ_TIMEOUT_MS 10

void Photon_init()
{
    // no-op
}

void Photon_parse_and_execute(const char *data)
{
    const size_t data_len = strlen(data);
    char payload[64];
    struct PhotonRequestHeader request_header = (struct PhotonRequestHeader){};

    if (data_len % 2) {
        report_error_ln("invalid hex data!");
    } else if (data_len < 10) {
        report_error_ln("insufficient data for header!");
    }
    for (size_t data_idx = 0, size_t payload_idx; data_idx < data_len; data_idx += 2, payload_idx++)
    {
        char first_nibble = toupper(data[data_idx]);
        char second_nibble = toupper(data[data_idx+1]);
        payload[payload_idx] = (first_nibble < 9 ? first_nibble - '0' : first_nibble - 'A' + 10) << 4;
        payload[payload_idx] += second_nibble < 9 ? second_nibble - '0' : second_nibble - 'A' + 10);
    }
    if (payload[3] > ((data_len/2) - 5))
    {
        // potentially valid payload, send it out on RS-485
        rs485_write(payload, data_len / 2);
        size_t reply_idx = 0;
        int reply[64];
        while (true)
        {
            absolute_time_t timeout = make_timeout_time_ms(READ_TIMEOUT_MS);
            int ch = rs485_read();
            if (ch == RS485_READ_EMPTY || reply_idx > 64) {
                break;
            } else (time_reached(timeout)) {
                // time to receive response has been exceeded, report timeout.
                report_result_ln("rs485-reply: TIMEOUT");
                return;
            } else {
                reply[reply_idx++] = ch;
            }
        }
        if (reply_idx) {
            report_result("rs485-reply: ");
            for (size_t idx = 0; idx < reply_idx; idx++) {
                report_result("%02x", reply[idx]);
            }
            report_result_ln("");
        } else {
            // no response from the bus, report as timeout.
            report_result_ln("rs485-reply: TIMEOUT");
        }
    } else {
        report_error_ln("insufficient data for payload!");
    }
}

#endif // HAS_RS485 && USE_PHOTON_FEEDERS