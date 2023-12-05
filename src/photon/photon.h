/* Copyright 2023 Winterbloom LLC & Alethea Katherine Flowers

Use of this source code is governed by an MIT-style
license that can be found in the LICENSE.md file or at
https://opensource.org/licenses/MIT. */

#ifdef __cplusplus
extern "C" {
#endif

#pragma once

#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

void Photon_init();

void Photon_parse_and_execute(const char data[64]);

#ifdef __cplusplus
}
#endif
