// Run: node tests/device-name.check.mts
import assert from "node:assert/strict";
// @ts-expect-error -- Node runs .ts imports directly; tsc does not allow the extension
import { deviceName } from "../lib/device-name.ts";
assert.equal(deviceName("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"), "Chrome on Windows");
assert.equal(deviceName("Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/126.0 Safari/537.36 Edg/126.0"), "Edge on Windows");
assert.equal(deviceName("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"), "Safari on iOS");
assert.equal(deviceName("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36"), "Chrome on Android");
assert.equal(deviceName(""), "Browser");
console.log("device-name ok");
