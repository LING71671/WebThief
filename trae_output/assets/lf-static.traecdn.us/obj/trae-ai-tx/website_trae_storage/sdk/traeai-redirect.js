/**
 * @file 如果用户直接访问 www.traeai.us，则重定向到 www.trae.ai
 * @description 通过 SCM 构建上传 JS 产物到 TTP CDN，再通过 www.traeai.us 的 TLB 配置，将该 JS 产物插入到 html 中
 */

/** 对部分路径进行豁免，可直接通过 www.traeai.us 访问 */
const REDIRECT_EXCLUDE_PATHS = []

function validateAndRedirect() {
  if (typeof location === 'undefined') {
    return
  }

  if (REDIRECT_EXCLUDE_PATHS.some((path) => location.pathname.includes(path))) {
    return
  }

  if (location.hostname !== 'www.traeai.us') {
    return
  }

  location.href = 'https://www.trae.ai/'
}

validateAndRedirect()
