/* eslint-disable @typescript-eslint/no-var-requires */
const { createProxyMiddleware } = require("http-proxy-middleware");
module.exports = function (app) {
  app.use(
    "/apiapi/v1/demo",
    createProxyMiddleware({
      target:
        "http://a6500b130ef7c45eb96f1727f55bafb6-1149103410.ap-southeast-1.elb.amazonaws.com",
      changeOrigin: true,
    })
  );
};
