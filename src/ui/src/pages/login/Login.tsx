import React, { useEffect, useState } from "react";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import { useHistory, RouteComponentProps } from "react-router-dom";
import Breadcrumbs from "@material-ui/core/Breadcrumbs";
import { useDispatch } from "redux-react-hook";
import { v4 as uuidv4 } from "uuid";
import { AxiosResponse } from "axios";
import Axios from "assets/utils/http";
import Header from "common/Header";
import { AppConfigType } from "common/types";
import {
  STORAGE_USER_NAME_KEY,
  STORAGE_USER_UUID_KEY,
  STORAGE_USER_VISIT_COUNT_KEY,
  VISITOR_ANOMY_ID,
} from "common/config/const";

import AppConfigContext from "common/AppConfigContext";

interface MatchParams {
  type: string;
}

const Login: React.FC<RouteComponentProps<MatchParams>> = (props) => {
  const history = useHistory();

  const type = props.match.params.type;
  console.info("type:", type);

  const appConfig: AppConfigType = React.useContext(
    AppConfigContext
  ) as AppConfigType;
  let API_URL = appConfig.NEWS_API_URL;
  if (type === "movie") {
    API_URL = appConfig.MOVIE_API_URL;
  }

  const [userName, setUserName] = useState<string | undefined>(undefined);
  const [needName, setNeedName] = useState(false);

  const dispatch = useDispatch();
  useEffect(() => {
    console.info("AAAA");
    dispatch({ type: "set current page", curPage: "HOME" });
  }, [dispatch]);

  const login = (callback: (res: AxiosResponse, userId: string) => void) => {
    localStorage.removeItem(STORAGE_USER_NAME_KEY);
    localStorage.removeItem(STORAGE_USER_UUID_KEY);
    const initUuid = uuidv4();
    const data = {
      userId: initUuid,
      userName: userName,
    };
    console.info("data.userId:", initUuid);
    Axios.post(API_URL + "/login", data)
      .then((res) => {
        if (callback) {
          callback(res.data, initUuid);
        }
      })
      .catch((err) => {
        console.error(err);
      });
  };

  const goToNextPage = () => {
    login((userInfo: AxiosResponse, initUuid: string) => {
      console.info("userInfo:", userInfo, initUuid);
      const curUserName = VISITOR_ANOMY_ID;
      const curUserId = initUuid;
      dispatch({
        type: "set current user",
        curUser: { userName: curUserName, userId: curUserId, visitCount: 1 },
      });
      // Save Data to Localstorage
      localStorage.setItem(STORAGE_USER_UUID_KEY, curUserId);
      localStorage.setItem(STORAGE_USER_NAME_KEY, curUserName);
      // localStorage.removeItem(STORAGE_USER_NAME_KEY);

      let toPath = "/news";
      if (type === "movie") {
        toPath = "/movie";
      }
      history.push({
        pathname: toPath,
      });
    });
  };

  const loginToSystem = () => {
    if (userName === undefined || userName?.trim() === "") {
      setNeedName(true);
      return;
    } else {
      // goToNews();
      login((userInfo: AxiosResponse, initUuid: string) => {
        console.info("userInfo:", userInfo, initUuid);
        const curUserName = userName;
        const curUserId = userInfo.data.userId;
        const visitCount = userInfo.data.visitCount;
        dispatch({
          type: "set current user",
          curUser: {
            userName: curUserName,
            userId: curUserId,
            visitCount: visitCount,
          },
        });
        // Save Data to Localstorage
        localStorage.setItem(STORAGE_USER_UUID_KEY, curUserId);
        localStorage.setItem(STORAGE_USER_NAME_KEY, curUserName);
        localStorage.setItem(STORAGE_USER_VISIT_COUNT_KEY, visitCount);

        let toPath = "/news";
        if (type === "movie") {
          toPath = "/movie";
        }
        history.push({
          pathname: toPath,
        });
      });
    }
  };

  return (
    <div>
      <Header />
      <div style={{ margin: "5px 0 10px 0" }}>
        <Breadcrumbs aria-label="breadcrumb">
          {/* <Typography color="textPrimary">首页</Typography> */}
        </Breadcrumbs>
      </div>
      <div>
        <div className="login-page">
          <div className="login-wrap">
            <TextField
              autoFocus
              error={needName}
              label="请输入您的用户名"
              helperText={needName ? "用户名不能为空" : " "}
              style={{ width: "100%" }}
              variant="outlined"
              onChange={(event) => {
                setNeedName(false);
                setUserName(event.target.value);
              }}
            />
            <div style={{ padding: "10px 0" }} className="text-right">
              <Button
                style={{ marginRight: "20px" }}
                onClick={() => {
                  setUserName(undefined);
                  goToNextPage();
                }}
                color="primary"
              >
                随便看看
              </Button>
              <Button
                onClick={loginToSystem}
                variant="contained"
                color="primary"
              >
                立即登录
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
