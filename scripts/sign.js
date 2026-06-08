#!/usr/bin/env node
/**
 * FlySource-sign 签名生成器
 *
 * 从小程序 wxapkg 提取的原版 MD5 + Base64 实现。
 * 作为 Python CLI 的签名后端，通过 subprocess 调用。
 *
 * 用法：
 *   node scripts/sign.js <path> <timestamp> <token>
 * 输出：
 *   <sign-string>
 */

const crypto = require('crypto');

function md5(s) {
    return crypto.createHash('md5').update(s, 'utf8').digest('hex');
}

function b64(str) {
    return Buffer.from(str, 'utf8').toString('base64');
}

function generateSign(path, timestamp, token) {
    const tsStr = String(timestamp);
    const inner = md5(tsStr + token);
    const outer = md5(path + '?sign=' + inner);
    return outer + '1.' + b64(tsStr);
}

// CLI mode
const args = process.argv.slice(2);
if (args.length >= 3) {
    const [path, ts, token] = args;
    console.log(generateSign(path, parseInt(ts), token));
} else if (args.length === 1 && args[0] === '--test') {
    // Self-test: compare with known values (fill in when available)
    console.log('Usage: node scripts/sign.js <path> <timestamp> <token>');
} else {
    console.error('Usage: node scripts/sign.js <path> <timestamp> <token>');
    process.exit(1);
}
