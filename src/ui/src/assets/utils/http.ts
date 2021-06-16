import axios from "axios";

import Swal from "sweetalert2";

const instance = axios.create({
  // baseURL: "/api/v1/demo",
  headers: {
    "Content-Type": "application/json",
  },
});

instance.interceptors.request.use(
  (config) => {
    return config;
  },
  function (error) {
    return Promise.reject(error);
  }
);

instance.interceptors.response.use(
  (response) => {
    console.info("response:", response);
    if (response.status === 401 || response.status === 403) {
      // Redirect to Authing Login
      return Promise.reject("401 User Unauthorized");
    } else {
      if (response) {
        return Promise.resolve(response);
      } else {
        return Promise.reject("response error");
      }
    }
  },
  (error) => {
    console.info("ERR:", error.response);
    // Swal.fire(error.message);
    Swal.fire(
      `${error.message}`,
      `${error?.response?.config?.url} \n ${
        error?.response?.config?.params
          ? JSON.stringify(error?.response?.config?.params)
          : ""
      }`,
      undefined
    );
    console.log("-- error --");
    console.error(error);
    console.log("-- error --");
    return Promise.reject({
      success: false,
      msg: error,
    });
  }
);

export default instance;
