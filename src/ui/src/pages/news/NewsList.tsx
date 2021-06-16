import React, { useEffect, useState, useContext } from "react";
// import IconImg from "assets/images/icon.jpg";
import { useTranslation } from "react-i18next";
import { Base64 } from "js-base64";
import randomColor from "randomcolor"; // import the script
import InfiniteScroll from "react-infinite-scroll-component";
import Button from "@material-ui/core/Button";

// import Button from "aws-northstar/components/Button";
import Breadcrumbs from "@material-ui/core/Breadcrumbs";
import Link from "@material-ui/core/Link";
import Typography from "@material-ui/core/Typography";
import { useHistory } from "react-router-dom";
import classNames from "classnames";
import { useMappedState } from "redux-react-hook";

// import FaceIcon from "@material-ui/icons/Face";
import IconButton from "@material-ui/core/IconButton";
import MuiDialogTitle from "@material-ui/core/DialogTitle";
import CloseIcon from "@material-ui/icons/Close";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import HistoryIcon from "@material-ui/icons/History";
import Paper from "@material-ui/core/Paper";
import { makeStyles } from "@material-ui/core/styles";
import Tabs from "@material-ui/core/Tabs";
import Tab from "@material-ui/core/Tab";
import CastIcon from "@material-ui/icons/Cast";
import AccessTimeIcon from "@material-ui/icons/AccessTime";
import PersonPinIcon from "@material-ui/icons/PersonPin";

import Axios from "assets/utils/http";
import ReactWordcloud, { OptionsProp, Word } from "react-wordcloud";
import { Resizable } from "re-resizable";
import SentimentVerySatisfiedIcon from "@material-ui/icons/SentimentVerySatisfied";
import DataLoading from "common/Loading";
import useWindowSize from "hooks/useWindowSize";

import AppConfigContext from "common/AppConfigContext";

import Header from "common/Header";
import { AppConfigType } from "common/types";
import {
  HOBBY_LIST,
  ENUM_NEWS_TYPE,
  STORAGE_USER_UUID_KEY,
  IMAGE_PATH,
  converListToMap,
  RS_ADMIN_USER_NAME,
  STORAGE_USER_NAME_KEY,
} from "common/config/const";
import { useDispatch } from "redux-react-hook";
import { IState } from "store/Store";

import "tippy.js/dist/tippy.css";
import "tippy.js/animations/scale.css";

const useStyles = makeStyles({
  root: {
    flexGrow: 1,
    // maxWidth: 500,
  },
});

type NewsType = {
  title: string;
  image?: string;
  desc?: string;
  tag?: string[];
  type: string;
  user_id: string;
  id: string;
};

const NEWS_TAG_MAP = converListToMap();

const mapState = (state: IState) => ({
  curUser: state.curUser,
});

const NewsList: React.FC = () => {
  const size = useWindowSize();
  const appConfig: AppConfigType = useContext(
    AppConfigContext
  ) as AppConfigType;
  const API_URL = appConfig.NEWS_API_URL;
  console.info("appConfig:", appConfig);

  const { curUser } = useMappedState(mapState);

  const userUuid =
    curUser?.userId || localStorage.getItem(STORAGE_USER_UUID_KEY);

  const curUserName =
    curUser?.userName || localStorage.getItem(STORAGE_USER_NAME_KEY);

  const [visible, setVisible] = useState(false);
  const history = useHistory();
  const [historyList, setHistoryList] = useState<Array<NewsType>>([]);
  const [newsList, setNewsList] = useState<Array<NewsType>>([]);
  const [newsHeight, setNewsHeight] = useState(() => {
    return window.innerWidth > 768
      ? window.innerHeight - 160
      : window.innerHeight - 160;
  });
  console.info("newsHeight:", newsHeight);
  const [historyHeight, setHistoryHeight] = useState(0);
  const [modalHeight, setModalHeight] = useState(0);
  const [loadingNews, setLoadingNews] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingPortrait, setLoadingPortrait] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  // const [detailContent, setDetailContent] = useState<NewsType>();
  const [selectType, setSelectType] = useState<string>(
    ENUM_NEWS_TYPE.RECOMMEND
  );
  const [newsUrl, setNewsUrl] = useState(" ");
  const [historyCount, setHistoryCount] = useState(0);
  const [portraitWords, setPortraitWords] = useState<Word[]>([]);
  const [curNewsName, setCurNewsName] = useState("");
  const [historyPageNumber, setHistoryPageNumber] = useState(0);
  const [showLoadTips, setShowLoadTips] = useState(false);
  const dispatch = useDispatch();

  const [isMobile, setIsMobile] = useState(false);
  const [mobileTransform, setMobileTransform] = useState(0);

  const classes = useStyles();
  const [tabIndex, setTabIndex] = React.useState("news");

  const handleChange = (
    event: React.ChangeEvent<unknown>,
    newValue: string
  ) => {
    console.info("newValue:", newValue);
    setTabIndex(newValue);
    if (newValue === "news") {
      setMobileTransform(0);
    }
    if (newValue === "history") {
      setMobileTransform(-size.width);
    }
    if (newValue === "portrait") {
      setMobileTransform(-size.width * 2);
    }
  };

  const { i18n } = useTranslation();
  useEffect(() => {
    i18n.changeLanguage("zh");
    dispatch({ type: "set current page", curPage: "NEWS" });
  }, [dispatch, i18n]);

  // const tagSize: MinMaxPair = [400, 200];
  const options: OptionsProp = {
    // colors: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
    fontFamily:
      "'-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', 'sans-serif'",
    fontSizes: [8, 30],
    fontStyle: "normal",
    fontWeight: "normal",
    scale: "sqrt",
    spiral: "archimedean",
    padding: 1,
    rotations: 50,
    rotationAngles: [0, 0],
  };

  const resizeStyle = {
    margin: "5px auto",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    height: "100%",
  };

  useEffect(() => {
    console.info("size:", size);
    if (size.width > 768) {
      setNewsHeight(size.height - 160);
      setHistoryHeight(size.height - 450);
      // Show All Comps
      setIsMobile(false);
    } else {
      setIsMobile(true);
      setNewsHeight(size.height - 160);
      setHistoryHeight(size.height - 200);
    }
    setModalHeight(size.height - 150);
  }, [size]);

  useEffect(() => {
    console.info("isMobile:", isMobile);
  }, [isMobile]);

  const handleClick = (event: React.MouseEvent) => {
    event.preventDefault();
    const toPath = "/";
    history.push({
      pathname: toPath,
    });
    console.info("You clicked a breadcrumb.");
  };

  const getNewsList = (type: string, loadMore = false) => {
    console.info("TYPE:", type);
    console.info("loadMore:", loadMore);
    // if (selectType) {
    const params = {
      userId: userUuid,
      // userId: "magic-uuid",
      type: type,
      curPage: 0,
      pageSize: 10,
    };
    if (!loadMore) {
      setLoadingNews(true);
      setNewsList([]);
    }
    Axios.get(API_URL + "/news", { params: params })
      .then((res) => {
        console.info("res:res:", res);
        setLoadingNews(false);
        if (res.data && res.data.data) {
          res.data.data.forEach((element: NewsType) => {
            const newsTag = element.type || "no-img";
            element.image = `${IMAGE_PATH}${newsTag}/${Math.floor(
              1 + Math.random() * (30 - 1)
            )}.jpg`;
          });
        }
        if (loadMore) {
          setNewsList((prev: NewsType[]) => {
            console.info("prev:", prev);
            console.info("res.data?.data:", res.data?.data);
            return [...prev, ...res.data?.data];
          });
        } else {
          setNewsList(res.data?.data || []);
        }
      })
      .catch((err) => {
        console.error(err);
        setLoadingNews(false);
      });
    // }
  };

  const getHistoryList = () => {
    const params = {
      curPage: 0,
      pageSize: 66,
    };
    setHistoryCount(0);
    setHistoryList([]);
    // setLoadingNews(true);
    setLoadingHistory(true);
    Axios.get(API_URL + "/click/" + userUuid, { params: params })
      .then((res) => {
        setLoadingHistory(false);
        console.info("res:res:", res);
        setHistoryList(res.data.data || []);
        setHistoryCount(res.data.totalItems);
      })
      .catch((err) => {
        setLoadingHistory(false);
        console.error(err);
      });
  };

  const loadMoreHistory = (pageNumber: number) => {
    const params = {
      curPage: pageNumber,
      pageSize: 20,
    };
    setHistoryCount(0);
    setHistoryList([]);
    // setLoadingNews(true);
    Axios.get(API_URL + "/click/" + userUuid, { params: params })
      .then((res) => {
        console.info("res:res:", res);
        if (res.data && res.data.data) {
          setHistoryList([...historyList, res.data.data]);
        }
      })
      .catch((err) => {
        console.error(err);
      });
  };

  const callbacks = {
    getWordColor: (word: Word) =>
      word.type === "ITEM" ? "#cccccc" : randomColor({ luminosity: "dark" }),
    onWordClick: console.log,
    onWordMouseOver: console.log,
    getWordTooltip: (word: Word) => `兴趣度:${word.value.toFixed(5)}`,
  };

  const getUserPortrait = () => {
    // setLoadingNews(true);
    setLoadingPortrait(true);
    Axios.get(API_URL + "/portrait/userid/" + userUuid)
      .then((res) => {
        setLoadingPortrait(false);
        console.info("portrait:res:", res);
        if (res.data && res.data.data) {
          const portraitData = res.data.data;
          const portraitArr = Object.keys(portraitData);
          console.info("portraitArr:", portraitArr);
          const tmpPortraitArr: Word[] = [];
          const typeArr = portraitData.type;
          const keywordsArr = portraitData.keywords;
          console.info("typeArr:", typeArr);
          console.info("keywordsArr:", keywordsArr);
          const typeScoreArr = [];
          if (typeArr) {
            for (let type in typeArr) {
              const typeObj = typeArr[type];
              if (type !== "recent") {
                typeScoreArr.push(typeObj.score);
                tmpPortraitArr.push({
                  text: NEWS_TAG_MAP[type]?.name,
                  value: typeObj.score,
                  type: "CLASS",
                });
              }
            }
          }
          if (typeScoreArr && typeScoreArr.length > 1) {
            const typeAvg =
              typeScoreArr.reduce((a, b) => a + b) / typeScoreArr.length;
            console.info("typeAvg:typeAvg:", typeAvg);
            if (keywordsArr) {
              for (let keyword in keywordsArr) {
                const typeObj = keywordsArr[keyword];
                const refScore = typeObj <= typeAvg ? typeObj : typeAvg;
                if (
                  keyword !== "recent" &&
                  (keyword.length === 2 || keyword.length === 3)
                ) {
                  tmpPortraitArr.push({
                    text: keyword,
                    value: refScore - 0.3 > 0 ? refScore - 0.3 : 0.0001,
                    type: "ITEM",
                  });
                }
              }
            }
          }
          console.info("tmpPortraitArr:", tmpPortraitArr);
          setPortraitWords(tmpPortraitArr);
        }
      })
      .catch((err) => {
        setLoadingPortrait(false);
        console.error(err);
      });
  };

  useEffect(() => {
    console.info("curNewsType:", selectType);
    getNewsList(selectType);
    getHistoryList();
    getUserPortrait();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addNewsToHistory = (item: NewsType) => {
    // item.title = "";
    // const encodedString = new Buffer(item.title).toString("base64");
    setCurNewsName(item.title);
    const encodedString = Base64.encode(item.title);
    setNewsUrl(" ");
    const titleData = {
      title: encodedString,
    };
    setVisible(true);
    setLoadingDetail(true);
    setShowLoadTips(true);
    const clickData = {
      userId: userUuid,
      itemId: item.id,
    };
    Axios.post(API_URL + "/click", clickData).then((clickRes) => {
      console.info("click Res", clickRes);
      const tmpList = [...historyList];
      tmpList.unshift(item);
      setHistoryList(tmpList);
      setHistoryCount(historyCount + 1);
      getUserPortrait();
      Axios.post(API_URL + "/url", titleData).then((newsRes) => {
        setNewsUrl(newsRes.data.url);
        setShowLoadTips(false);
      });
    });
  };

  const goToDashboard = () => {
    history.push("/news/dashboard");
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
            <Typography color="textPrimary">新闻推荐列表</Typography>
          </Breadcrumbs>
          <div className="dashboard-link">
            {!isMobile && curUserName === RS_ADMIN_USER_NAME && (
              <Button
                variant="outlined"
                size="small"
                onClick={() => {
                  goToDashboard();
                }}
              >
                管理仪表盘
              </Button>
            )}
            {/* <a className="link" href="/#/news/dashboard">
              仪表盘
            </a> */}
          </div>
        </div>
        <div
          className="news-list-wrap"
          style={{
            width: isMobile ? size.width * 3 : "auto",
            transform: isMobile
              ? `translate(${mobileTransform}px, 0px)`
              : "none",
          }}
        >
          <div className={classNames("list")}>
            <div className="type-item">
              <div className="menu-list">
                {HOBBY_LIST.map((element, index) => {
                  const active = element.value === selectType;
                  return (
                    <span
                      className={classNames("m-item", {
                        active: active,
                        "no-show": element.value === "stock",
                      })}
                      onClick={() => {
                        setSelectType(element.value);
                        getNewsList(element.value);
                      }}
                      key={index}
                    >
                      {element.name}
                    </span>
                  );
                })}
              </div>
            </div>
            <div className="news-list" style={{ height: newsHeight }}>
              {!loadingNews && newsList.length <= 0 && (
                <div className="no-data">暂无数据</div>
              )}
              <InfiniteScroll
                dataLength={newsList.length} //This is important field to render the next data
                next={() => {
                  console.info("NEXT");
                  getNewsList(selectType, true);
                }}
                height={newsHeight}
                hasMore={true}
                loader={
                  <div className="text-center">
                    <DataLoading />
                  </div>
                }
                endMessage={
                  <p style={{ textAlign: "center" }}>
                    <b>我是有底线的</b>
                  </p>
                }
                // below props only if you need pull down functionality
                refreshFunction={() => {
                  getNewsList(selectType);
                }}
                pullDownToRefresh
                pullDownToRefreshThreshold={50}
                pullDownToRefreshContent={
                  <div
                    style={{
                      paddingTop: 10,
                      color: "#888",
                      textAlign: "center",
                    }}
                  >
                    &#8595; 下拉刷新
                  </div>
                }
                releaseToRefreshContent={
                  <div
                    style={{
                      paddingTop: 10,
                      color: "#888",
                      textAlign: "center",
                    }}
                  >
                    &#8593; 松开刷新
                  </div>
                }
              >
                {newsList.map((item: NewsType, index: number) => {
                  const typeStr = item.type;
                  const trueTypeName = NEWS_TAG_MAP[typeStr]?.name || "";
                  return (
                    <li key={index} className="item">
                      <div
                        className="icon"
                        style={{ backgroundImage: `url(${item.image})` }}
                      >
                        <span className="mask">Example</span>
                        {/* <img alt="icon" src={item.image} width="100%" /> */}
                      </div>
                      <div className="content">
                        {item.tag?.[0] === ENUM_NEWS_TYPE.COLDSTART &&
                          selectType === ENUM_NEWS_TYPE.RECOMMEND && (
                            <span className="flag-icon cold-start">冷启</span>
                          )}
                        {item.tag?.[0] === ENUM_NEWS_TYPE.RECOMMEND &&
                          selectType === ENUM_NEWS_TYPE.RECOMMEND && (
                            <span className="flag-icon recommand">推荐</span>
                          )}
                        {item.tag?.[0] === ENUM_NEWS_TYPE.DIVERSITY &&
                          selectType === ENUM_NEWS_TYPE.RECOMMEND && (
                            <span className="flag-icon diversity">多样性</span>
                          )}
                        <div className="name">
                          <div>
                            <span
                              onClick={() => {
                                addNewsToHistory(item);
                              }}
                              className="a-link"
                            >
                              {item.title}
                            </span>
                            <div className="tag">
                              <span className="tag-item">{trueTypeName}</span>
                            </div>
                          </div>
                        </div>
                        <div className="desc">{item.desc}</div>

                        <div className="date">今天</div>
                      </div>
                    </li>
                  );
                })}
              </InfiniteScroll>
              {/* <div className="text-center margin-10">点击加载更多</div> */}
            </div>
          </div>
          <div
            className="history"
            style={{ width: isMobile ? size.width * 2 : "25rem" }}
          >
            <div
              className={classNames("history-content")}
              style={{ width: isMobile ? size.width : "auto" }}
            >
              <div className="icon-title">
                <HistoryIcon className="icon" />
                阅读历史记录
                <div className="history-count">
                  历史总阅读: <b>{historyCount}</b>篇
                </div>
              </div>
              <div>
                <div className="rs-list" style={{ height: historyHeight }}>
                  {/* {JSON.stringify({ list: historyList })} */}
                  <ul>
                    {loadingHistory && (
                      <div className="text-center">
                        <DataLoading />
                      </div>
                    )}
                    {!loadingHistory && historyList.length <= 0 && (
                      <div className="no-data">
                        暂无历史，请浏览感兴趣的新闻
                      </div>
                    )}
                    {historyList.map((element: NewsType, index: number) => {
                      return (
                        <li
                          onClick={() => {
                            addNewsToHistory(element);
                          }}
                          className="history-item"
                          key={index}
                        >
                          {element.title}
                        </li>
                      );
                    })}
                    {true && (
                      <div>
                        <span
                          onClick={() => {
                            setHistoryPageNumber(historyPageNumber + 1);
                            loadMoreHistory(historyPageNumber + 1);
                          }}
                        >
                          {/* 加载更多 */}
                        </span>
                      </div>
                    )}
                  </ul>
                </div>
              </div>
            </div>
            <div
              className={classNames("profile-content")}
              style={{
                width: isMobile ? size.width : "auto",
              }}
            >
              <div className="icon-title">
                <SentimentVerySatisfiedIcon className="icon" />
                用户画像
              </div>
              <div>
                {loadingPortrait && (
                  <div className="text-center">
                    <DataLoading />
                  </div>
                )}
                {!loadingPortrait && portraitWords.length <= 0 && (
                  <div className="no-data">暂无用户画像，请浏览新闻</div>
                )}
                {!loadingPortrait && (
                  <Resizable
                    defaultSize={{
                      width: 300,
                      height: 220,
                    }}
                    style={resizeStyle}
                  >
                    <div
                      style={{
                        width: "100%",
                        height: "100%",
                      }}
                    >
                      <ReactWordcloud
                        // maxWords={100}
                        callbacks={callbacks}
                        options={options}
                        words={portraitWords}
                      />
                    </div>
                  </Resizable>
                )}
                {/* <ReactWordcloud options={options} size={tagSize} words={words} /> */}
              </div>
            </div>
          </div>
        </div>
        <div className="bottom-tab">
          <Paper square className={classes.root}>
            <Tabs
              value={tabIndex}
              onChange={(event: React.ChangeEvent<unknown>, value) => {
                handleChange(event, value);
              }}
              variant="fullWidth"
              indicatorColor="primary"
              textColor="primary"
              aria-label="icon label tabs example"
            >
              <Tab value="news" icon={<CastIcon />} label="新闻列表" />
              <Tab value="history" icon={<AccessTimeIcon />} label="历史记录" />
              <Tab value="portrait" icon={<PersonPinIcon />} label="用户画像" />
            </Tabs>
          </Paper>
        </div>
      </div>
      <Dialog
        open={visible}
        onClose={() => setVisible(false)}
        fullWidth={true}
        maxWidth="lg"
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        {/* <DialogTitle id="alert-dialog-title">新闻详细信息</DialogTitle> */}
        <MuiDialogTitle disableTypography>
          <Typography style={{ paddingRight: "50px" }} variant="h6">
            {curNewsName}
          </Typography>
          <IconButton
            onClick={() => {
              setVisible(false);
            }}
            style={{ position: "absolute", right: "10px", top: "5px" }}
            aria-label="close"
          >
            <CloseIcon />
          </IconButton>
        </MuiDialogTitle>
        <DialogContent>
          {loadingDetail && (
            <div className="text-center">
              {newsUrl !== "" && (
                <div>
                  <DataLoading />
                  {showLoadTips && (
                    <div style={{ color: "#999" }}>
                      新闻详情来自第三方网站，返回速度受网络限制，请耐心等待
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <div className="news-detail">
            {newsUrl === "" ? (
              <span>暂时无法获取新闻详细内容</span>
            ) : (
              <iframe
                title="newsDetail"
                width="100%"
                height={modalHeight - 100 + "px"}
                src={newsUrl}
                onLoad={() => {
                  setLoadingDetail(false);
                }}
                onError={() => {
                  setLoadingDetail(false);
                }}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              ></iframe>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default NewsList;
