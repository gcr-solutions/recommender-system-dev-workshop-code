import React, { useState, useEffect, useContext, useCallback } from "react";
import { useMappedState } from "redux-react-hook";
import Breadcrumbs from "@material-ui/core/Breadcrumbs";
import Link from "@material-ui/core/Link";
import Typography from "@material-ui/core/Typography";
import { useHistory } from "react-router";
import Drawer from "@material-ui/core/Drawer";
import Button from "@material-ui/core/Button";
import MenuOpenIcon from "@material-ui/icons/MenuOpen";
import WhatshotIcon from "@material-ui/icons/Whatshot";
import BarChartIcon from "@material-ui/icons/BarChart";
import LibraryBooksIcon from "@material-ui/icons/LibraryBooks";
import TouchAppIcon from "@material-ui/icons/TouchApp";
import PersonIcon from "@material-ui/icons/Person";
import Header from "common/Header";
import TrainStatus from "./comp/TrainStatus";
import CategoryBarChart, { BarChartProps } from "./comp/CategoryBarChart";
import ClickLineChart, { LineChartProps } from "./comp/ClickLineChart";
import classNames from "classnames";
import Axios from "assets/utils/http";
import { format } from "date-fns";

import DataLoading from "common/Loading";
import AppConfigContext from "common/AppConfigContext";
import { AppConfigType } from "common/types";
import useInterval from "hooks/useInterval";
import {
  converListToMap,
  STORAGE_CONTENT_ARN_ID,
  STORAGE_MODEL_ARN_ID,
  STORAGE_ACTION_ARN_ID,
  STORAGE_CONTENT_ARN_URL,
  STORAGE_MODEL_ARN_URL,
  STORAGE_ACTION_ARN_URL,
  ENUM_SETTING_TYPE,
  RS_ADMIN_USER_NAME,
  STORAGE_USER_NAME_KEY, STORAGE_USER_ARN_ID, STORAGE_USER_ARN_URL,
} from "common/config/const";

import "./dashboard.scss";
import { IState } from "store/Store";

const mapState = (state: IState) => ({
  curUser: state.curUser,
});
interface UserCountType {
  totalUser: number;
  registerUser: number;
  anonymousUser: number;
}

enum ACTION_STATUS {
  ABORTED = "ABORTED",
  RUNNING = "RUNNING",
  SUCCEEDED = "SUCCEEDED",
  FAILED = "FAILED",
}

const NEWS_TAG_MAP: any = converListToMap();

const NewsDashboard: React.FC = () => {
  const appConfig: AppConfigType = useContext(
    AppConfigContext
  ) as AppConfigType;
  const API_URL = appConfig.NEWS_API_URL;
  console.info("API_URL:", API_URL);

  const { curUser } = useMappedState(mapState);
  const curUserName =
    curUser?.userName || localStorage.getItem(STORAGE_USER_NAME_KEY);

  const history = useHistory();
  const [anchor, setAnchor] = useState(false);
  const handleClick = (event: React.MouseEvent) => {
    event.preventDefault();
    const toPath = "/";
    history.push({
      pathname: toPath,
    });
    console.info("You clicked a breadcrumb.");
  };

  const [loadingData, setLoadingData] = useState(false);
  // Data
  const [reportTime, setReportTime] = useState(0);
  const [totalNewsCount, setTotalNewsCount] = useState(0);
  const [clickRatio, setClickRatio] = useState(0);
  const [coverRatio, setCoverRatio] = useState(0);
  const [userCount, setUserCount] = useState<UserCountType>({
    totalUser: 0,
    registerUser: 0,
    anonymousUser: 0,
  });
  const [totalNewsClick, setTotalNewsClick] = useState(0);
  const [newsRankList, setNewsRankList] = useState([]);
  const [userRankList, setUserRankList] = useState([]);
  // Bar Chart Data
  const [barChartData, setBarChartData] = useState<BarChartProps>();
  // Line Chart Data
  const [lineChartData, setlineChartData] = useState<LineChartProps>();

  // Settings Button Disable
  const [contentBtnDisabled, setContentBtnDisabled] = useState(true);
  const [userBtnDisabled, setUserBtnDisabled] = useState(true);
  const [modelBtnDisabled, setModelBtnDisabled] = useState(true);
  const [actionBtnDisabled, setActionBtnDisabled] = useState(true);

  // Interval Runing in diff setting action
  const [contentIsRuning, setContentIsRuning] = useState(true);
  const [contentSuccess, setContentSuccess] = useState(false);
  const [contentFailed, setContentFailed] = useState(false);
  const [contentArnURL, setContentArnURL] = useState("");

  const [userIsRuning, setUserIsRuning] = useState(true);
  const [userSuccess, setUserSuccess] = useState(false);
  const [userFailed, setUserFailed] = useState(false);
  const [userArnURL, setUserArnURL] = useState("");


  const [modelIsRuning, setModelIsRuning] = useState(true);
  const [modelSuccess, setModelSuccess] = useState(false);
  const [modelFailed, setModelFailed] = useState(false);
  const [modelArnURL, setModelArnURL] = useState("");

  const [actionIsRuning, setActionIsRuning] = useState(true);
  const [actionSuccess, setActionSuccess] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  const [actionArnURL, setActionArnURL] = useState("");

  // Interval Hook to monitor settings status

  const CHECK_DELAY_INTERVAL = 5000;

  const getArnStatus = useCallback(
    async (arn: string) => {
      return Axios.get(API_URL + "/offline_status/" + arn);
    },
    [API_URL]
  );

  useEffect(() => {
    if (curUserName !== RS_ADMIN_USER_NAME) {
      history.push({
        pathname: "/news",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [curUserName]);

  useInterval(
    () => {
      // Your custom logic here
      const storageContentArn =
        localStorage.getItem(STORAGE_CONTENT_ARN_ID) || "";
      const storageContentArnUrl =
        localStorage.getItem(STORAGE_CONTENT_ARN_URL) || "";
      setContentArnURL(storageContentArnUrl);
      console.info("storageContentArn:", storageContentArn);
      if (storageContentArn) {
        getArnStatus(storageContentArn).then((res) => {
          console.info("getContentArnStatus:RES:", res);
          const contentStatus = res.data.status;
          if (contentStatus === ACTION_STATUS.RUNNING) {
            console.info("Content Action is RUNING");
            setContentBtnDisabled(true);
          }
          if (
            contentStatus === ACTION_STATUS.FAILED ||
            contentStatus === ACTION_STATUS.ABORTED
          ) {
            console.info("Content Action is FAILED");
            setContentFailed(true);
            setContentIsRuning(false);
            setContentBtnDisabled(false);
          }
          if (contentStatus === ACTION_STATUS.SUCCEEDED) {
            console.info("Content Action is SUCCESSED");
            setContentSuccess(true);
            setContentIsRuning(false);
            setContentBtnDisabled(false);
          }
        });
      } else {
        setContentIsRuning(false);
        setContentBtnDisabled(false);
      }
    },
    contentIsRuning ? CHECK_DELAY_INTERVAL : null
  );

  useInterval(
    () => {
      // Your custom logic here
      const storageUserArn =
        localStorage.getItem(STORAGE_USER_ARN_ID) || "";
      const storageUserArnUrl =
        localStorage.getItem(STORAGE_USER_ARN_URL) || "";
      setUserArnURL(storageUserArnUrl);
      console.info("storageUserArn:", storageUserArn);
      if (storageUserArn) {
        getArnStatus(storageUserArn).then((res) => {
          console.info("getUserArnStatus:RES:", res);
          const userStatus = res.data.status;
          if (userStatus === ACTION_STATUS.RUNNING) {
            console.info("User Action is RUNING");
            setUserBtnDisabled(true);
          }
          if (
            userStatus === ACTION_STATUS.FAILED ||
            userStatus === ACTION_STATUS.ABORTED
          ) {
            console.info("User Action is FAILED");
            setUserFailed(true);
            setUserIsRuning(false);
            setUserBtnDisabled(false);
          }
          if (userStatus === ACTION_STATUS.SUCCEEDED) {
            console.info("User Action is SUCCESSED");
            setUserSuccess(true);
            setUserIsRuning(false);
            setUserBtnDisabled(false);
          }
        });
      } else {
        setUserIsRuning(false);
        setUserBtnDisabled(false);
      }
    },
    userIsRuning ? CHECK_DELAY_INTERVAL : null
  );

  useInterval(
    () => {
      // Your custom logic here
      const storageModelArn = localStorage.getItem(STORAGE_MODEL_ARN_ID) || "";
      const storageModelArnUrl =
        localStorage.getItem(STORAGE_MODEL_ARN_URL) || "";
      setModelArnURL(storageModelArnUrl);
      console.info("storageModelArn:", storageModelArn);
      if (storageModelArn) {
        getArnStatus(storageModelArn).then((res) => {
          console.info("getModelArnStatus:RES:", res);
          const modelStatus = res.data.status;
          if (modelStatus === ACTION_STATUS.RUNNING) {
            console.info("Model Action is RUNING");
            setModelBtnDisabled(true);
          }
          if (
            modelStatus === ACTION_STATUS.FAILED ||
            modelStatus === ACTION_STATUS.ABORTED
          ) {
            setModelFailed(true);
            setModelIsRuning(false);
            setModelBtnDisabled(false);
          }
          if (modelStatus === ACTION_STATUS.SUCCEEDED) {
            setModelSuccess(true);
            setModelIsRuning(false);
            setModelBtnDisabled(false);
          }
        });
      } else {
        setModelIsRuning(false);
        setModelBtnDisabled(false);
      }
    },
    modelIsRuning ? CHECK_DELAY_INTERVAL : null
  );

  useInterval(
    () => {
      // Your custom logic here
      const storageActionArn =
        localStorage.getItem(STORAGE_ACTION_ARN_ID) || "";
      const storageActionArnUrl =
        localStorage.getItem(STORAGE_ACTION_ARN_URL) || "";
      setActionArnURL(storageActionArnUrl);
      console.info("storageActionArn:", storageActionArn);
      if (storageActionArn) {
        getArnStatus(storageActionArn).then((res) => {
          console.info("getActionArnStatus:RES:", res);
          const actionStatus = res.data.status;
          if (actionStatus === ACTION_STATUS.RUNNING) {
            console.info("Action Action is RUNING");
            setActionBtnDisabled(true);
          }
          if (
            actionStatus === ACTION_STATUS.FAILED ||
            actionStatus === ACTION_STATUS.ABORTED
          ) {
            setActionFailed(true);
            setActionIsRuning(false);
            setActionBtnDisabled(false);
          }
          if (actionStatus === ACTION_STATUS.SUCCEEDED) {
            setActionSuccess(true);
            setActionIsRuning(false);
            setActionBtnDisabled(false);
          }
        });
      } else {
        setActionIsRuning(false);
        setActionBtnDisabled(false);
      }
    },
    actionIsRuning ? CHECK_DELAY_INTERVAL : null
  );

  useEffect(() => {
    setLoadingData(true);
    Axios.get(API_URL + "/dashboard")
      .then((res) => {
        setLoadingData(false);
        console.info("RES:", res);
        const dataObj = res.data;
        // Set Dashboard Data
        setReportTime(dataObj.report_time);
        setTotalNewsCount(dataObj.total_item_count);
        setClickRatio(dataObj.item_click_ratio);
        setCoverRatio(dataObj.recommender_click_cover_ratio);
        setTotalNewsClick(dataObj.total_click_count);
        setNewsRankList(dataObj.top_items);
        setUserRankList(dataObj.top_users);
        setUserCount({
          totalUser: dataObj.total_user_count,
          registerUser: dataObj.register_user_count,
          anonymousUser: dataObj.anonymous_user_count,
        });
        // Build Bar Chart Data
        const clickCountBySource = dataObj.click_count_by_source;
        clickCountBySource.sort((a: any, b: any) =>
          a.count > b.count ? -1 : 1
        );
        const tmpCategroyList: string[] = [];
        const tmpClickList: number[] = [];
        clickCountBySource.forEach((element: any) => {
          if (element.source !== "recommend") {
            tmpCategroyList.push(NEWS_TAG_MAP[element.source]?.name || "");
            tmpClickList.push(element.count);
          }
        });
        setBarChartData({
          chartData: {
            categoryList: tmpCategroyList,
            clickCountList: tmpClickList,
          },
        });
        // Build Line Chart Data
        const timeWindowData = dataObj.click_count_recommender_time_window;
        const tmpTimeArr: string[] = [];
        const tmpNormalArr: number[] = [];
        const tmpRecommendArr: number[] = [];
        timeWindowData.forEach((element: any) => {
          if (element.is_recommender) {
            tmpTimeArr.push(
              format(new Date(element.end_time * 1000), "MM-dd HH:mm")
            );
            tmpRecommendArr.push(element.count);
          } else {
            tmpNormalArr.push(element.count);
          }
        });
        setlineChartData({
          lineChartData: {
            timeCategoryList: tmpTimeArr,
            normalCLickName: "常规点击次数",
            normalClickList: tmpNormalArr,
            recommendClickName: "基于推荐的点击次数",
            recommendClickList: tmpRecommendArr,
          },
        });
      })
      .catch((err) => {
        setLoadingData(false);
        console.error("ERR:", err);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // System Setting button Click
  const startSystemTrain = (type: string) => {
    // type: CONTENT/MODEL/ACTION
    if (type === ENUM_SETTING_TYPE.ACTION) {
      // STORAGE_ACTION_ARN_ID && localStorage.remove(STORAGE_ACTION_ARN_ID);
      // STORAGE_ACTION_ARN_URL && localStorage.remove(STORAGE_ACTION_ARN_URL);
      setActionBtnDisabled(true);
      setActionArnURL("");
    }
    if (type === ENUM_SETTING_TYPE.MODEL) {
      setModelBtnDisabled(true);
      setModelArnURL("");
    }
    if (type === ENUM_SETTING_TYPE.CONTENT) {
      setContentBtnDisabled(true);
      setContentArnURL("");
    }
    if (type === ENUM_SETTING_TYPE.USER) {
      setUserBtnDisabled(true);
      setUserArnURL("");
    }

    Axios.post(API_URL + "/start_train", { change_type: type }).then((res) => {
      console.info("res:", res);
      const resArn = res.data?.data?.executionArn || "";
      const resArnURL = res.data?.data?.detailUrl || "";
      if (type === ENUM_SETTING_TYPE.CONTENT) {
        localStorage.setItem(STORAGE_CONTENT_ARN_ID, resArn);
        localStorage.setItem(STORAGE_CONTENT_ARN_URL, resArnURL);
        setContentIsRuning(true);
      }

      if (type === ENUM_SETTING_TYPE.USER) {
        localStorage.setItem(STORAGE_USER_ARN_ID, resArn);
        localStorage.setItem(STORAGE_USER_ARN_URL, resArnURL);
        setUserIsRuning(true);
      }

      if (type === ENUM_SETTING_TYPE.MODEL) {
        localStorage.setItem(STORAGE_MODEL_ARN_ID, resArn);
        localStorage.setItem(STORAGE_MODEL_ARN_URL, resArnURL);
        setModelIsRuning(true);
      }
      if (type === ENUM_SETTING_TYPE.ACTION) {
        localStorage.setItem(STORAGE_ACTION_ARN_ID, resArn);
        localStorage.setItem(STORAGE_ACTION_ARN_URL, resArnURL);
        setActionIsRuning(true);
      }
    });
  };

  return (
    <div className="rs-app">
      <Header />
      <div className="rs-container">
        <div className="breadcrumb">
          <Breadcrumbs aria-label="breadcrumb">
            <Link color="inherit" href="/#/" onClick={handleClick}>
              首页
            </Link>
            <Link color="inherit" href="/#/news">
              新闻
            </Link>
            <Typography color="textPrimary">新闻统计仪表盘</Typography>
            <span style={{ fontSize: 14 }}>
              {reportTime
                ? "统计时间: " +
                  format(new Date(reportTime * 1000), "yyyy-MM-dd HH:mm:ss")
                : ""}
            </span>
          </Breadcrumbs>
          <span className="open-setting">
            <Button
              style={{ marginRight: 15 }}
              size="small"
              variant="outlined"
              onClick={() => {
                history.push({
                  pathname: "/news",
                });
              }}
            >
              新闻首页
            </Button>

            <Button
              startIcon={<MenuOpenIcon />}
              size="small"
              variant="outlined"
              onClick={() => {
                setAnchor(true);
              }}
            >
              系统设置
            </Button>
          </span>
        </div>

        {loadingData ? (
          <div className="text-center">
            <DataLoading />
          </div>
        ) : (
          <div className="dashboard-wrap">
            <div className="summary-card">
              <div className="card summary">
                <span className="title-icon">
                  <LibraryBooksIcon className="m-icon" />
                </span>
                <div className="name">新闻总数</div>
                <div className="count">
                  {totalNewsCount.toLocaleString()}
                  <span className="suffix">条</span>
                </div>
                <div className="sub-title">
                  推荐物品覆盖率:
                  <b>{(coverRatio * 100).toFixed(2)}</b>%
                </div>
                {/* <div className="icon">ICON</div> */}
              </div>
              <div className="card summary">
                <span className="title-icon">
                  <PersonIcon className="m-icon" />
                </span>
                <div className="name">用户总数</div>
                <div className="count">
                  {userCount.totalUser.toLocaleString()}
                  <span className="suffix">个</span>
                </div>
                <div className="sub-title">
                  注册用户: <b>{userCount.registerUser.toLocaleString()}</b>{" "}
                  游客: <b>{userCount.anonymousUser.toLocaleString()}</b>
                </div>
                {/* <div className="icon">ICON</div> */}
              </div>
              <div className="card summary">
                <span className="title-icon">
                  <TouchAppIcon className="m-icon" />
                </span>
                <div className="name">新闻总点击次数</div>
                <div className="count">
                  {totalNewsClick.toLocaleString()}
                  <span className="suffix">次</span>
                </div>
                <div className="sub-title">
                  推荐物品点击率: <b>{(clickRatio * 100).toFixed(2)}</b>%
                </div>
                {/* <div className="icon">ICON</div> */}
              </div>
              <div className="card hot">
                <div className="chart-title">
                  <span className="icon">
                    <WhatshotIcon />
                  </span>
                  热门分类点击
                </div>
                <CategoryBarChart
                  chartData={{
                    categoryList: barChartData?.chartData?.categoryList || [],
                    clickCountList:
                      barChartData?.chartData?.clickCountList || [],
                  }}
                />
              </div>
            </div>
            <div className="hot-chart">
              <div className="card chart">
                <div className="chart-title">
                  <span className="icon">
                    <BarChartIcon />
                  </span>
                  用户点击趋势图
                </div>
                <ClickLineChart
                  lineChartData={{
                    timeCategoryList:
                      lineChartData?.lineChartData?.timeCategoryList || [],
                    normalCLickName:
                      lineChartData?.lineChartData?.normalCLickName || "",
                    normalClickList:
                      lineChartData?.lineChartData?.normalClickList || [],
                    recommendClickName:
                      lineChartData?.lineChartData.recommendClickName || "",
                    recommendClickList:
                      lineChartData?.lineChartData?.recommendClickList || [],
                  }}
                />
              </div>
              <div className="card news">
                <div className="chart-title">
                  <span className="icon">
                    <WhatshotIcon />
                  </span>
                  热点新闻
                </div>
                <div className="hot-mews-rank">
                  {newsRankList.map((element: any, index) => {
                    return (
                      <div key={index} className="hot-item">
                        <div className={index < 3 ? "rank top" : "rank"}>
                          <span>{index + 1}</span>
                        </div>
                        <div className="title" title={element.title}>
                          {element.title}
                        </div>
                        <div className="icon">
                          <span
                            className={classNames({
                              "no-show": index > 2,
                            })}
                          >
                            热
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="card user">
                <div className="chart-title">
                  <span className="icon">
                    <PersonIcon />
                  </span>
                  活跃用户
                </div>
                <div className="acitve-user-rank">
                  {userRankList.map((element: any, index) => {
                    return (
                      <div key={index} className="active-user-item">
                        <div
                          className={index < 3 ? "user-rank top" : "user-rank"}
                        >
                          <span>{index + 1}</span>
                        </div>
                        <div className="user-name">{element.name}</div>
                        <div className="user-count">
                          {/* {element.count} */}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      <React.Fragment key="right">
        <Drawer
          anchor="right"
          open={anchor}
          onClose={() => {
            setAnchor(false);
          }}
        >
          <div className="sys-setting">
            <div className="title">系统设置</div>
            <div className="btn">
              <Button
                disabled={contentBtnDisabled}
                color="primary"
                variant="contained"
                onClick={() => {
                  setContentFailed(false);
                  setContentSuccess(false);
                  startSystemTrain(ENUM_SETTING_TYPE.CONTENT);
                }}
              >
                物品上线
              </Button>

              <TrainStatus
                statusRunning={contentIsRuning}
                statusSuccess={contentSuccess}
                statusFailed={contentFailed}
                arnUrl={contentArnURL}
              />
              <div className="tips">添加新的物品信息到推荐系统</div>
            </div>

            <div className="btn">
              <Button
                disabled={userBtnDisabled}
                color="primary"
                variant="contained"
                onClick={() => {
                  setUserFailed(false);
                  setUserSuccess(false);
                  startSystemTrain(ENUM_SETTING_TYPE.USER);
                }}
              >
                新用户上线
              </Button>

              <TrainStatus
                statusRunning={userIsRuning}
                statusSuccess={userSuccess}
                statusFailed={userFailed}
                arnUrl={userArnURL}
              />
              <div className="tips">添加新的用户信息到推荐系统</div>
            </div>


            <div className="btn">
              <Button
                disabled={modelBtnDisabled}
                color="primary"
                variant="contained"
                onClick={() => {
                  setModelFailed(false);
                  setModelSuccess(false);
                  startSystemTrain(ENUM_SETTING_TYPE.MODEL);
                }}
              >
                模型训练
              </Button>

              <TrainStatus
                statusRunning={modelIsRuning}
                statusSuccess={modelSuccess}
                statusFailed={modelFailed}
                arnUrl={modelArnURL}
              />
              <div className="tips">根据累计的行为数据训练模型</div>
            </div>
            <div className="btn">
              <Button
                disabled={actionBtnDisabled}
                color="primary"
                variant="contained"
                onClick={() => {
                  setActionFailed(false);
                  setActionSuccess(false);
                  startSystemTrain(ENUM_SETTING_TYPE.ACTION);
                }}
              >
                批量处理
              </Button>
              <TrainStatus
                statusRunning={actionIsRuning}
                statusSuccess={actionSuccess}
                statusFailed={actionFailed}
                arnUrl={actionArnURL}
              />
              <div className="tips">
                根据系统内用户的历史信息批量生成推荐列表
              </div>
            </div>
          </div>
        </Drawer>
      </React.Fragment>
    </div>
  );
};

export default NewsDashboard;
