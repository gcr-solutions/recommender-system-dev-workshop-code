import React, { useState, useEffect, useCallback, useRef } from "react";
import { useDispatch } from "redux-react-hook";
import { useTranslation } from "react-i18next";
import LazyLoad from "react-lazyload";
import Axios from "assets/utils/http";
import { useHistory } from "react-router-dom";
import Breadcrumbs from "@material-ui/core/Breadcrumbs";
import Link from "@material-ui/core/Link";
import Typography from "@material-ui/core/Typography";
import Button from "@material-ui/core/Button";

import { MovieType, MOVIE_TYPE_LIST } from "common/types";
import Loader from "react-loader-spinner";
import { AppConfigType } from "common/types";
import useWindowSize from "hooks/useWindowSize";
import { useMappedState } from "redux-react-hook";

import Header from "common/Header";
import SlideItem from "./comp/SlideItem";
import Portrait from "./comp/Portrait";
import {
  RS_ADMIN_USER_NAME,
  STORAGE_USER_NAME_KEY,
  STORAGE_USER_UUID_KEY,
} from "common/config/const";
import AppConfigContext from "common/AppConfigContext";

import "./Movie.scss";
import { IState } from "store/Store";

const mapState = (state: IState) => ({
  curUser: state.curUser,
});

const MovieList: React.FC = () => {
  const dispatch = useDispatch();
  const history = useHistory();
  const size = useWindowSize();
  const [isMobile, setIsMobile] = useState(false);

  const { i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [curUserId, setCurUserId] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [historyData, setHistoryData] = useState<MovieType[]>([]);
  // const [showPortrait, setShowPortrait] = useState(true);
  const portraitRef: any = useRef();

  const { curUser } = useMappedState(mapState);
  const curUserName =
    curUser?.userName || localStorage.getItem(STORAGE_USER_NAME_KEY);

  const appConfig: AppConfigType = React.useContext(
    AppConfigContext
  ) as AppConfigType;

  const API_URL = appConfig.MOVIE_API_URL;

  useEffect(() => {
    console.info("size:", size);
    if (size.width > 768) {
      // Show All Comps
      setIsMobile(false);
    } else {
      setIsMobile(true);
    }
  }, [size]);

  useEffect(() => {
    dispatch({ type: "set current page", curPage: "MOVIE" });
    i18n.changeLanguage("en");
  }, [dispatch, i18n]);

  // Login when localstorage has user info, otherwise redirect to login
  useEffect(() => {
    const storageUserName = localStorage.getItem(STORAGE_USER_NAME_KEY);
    const storageUserId = localStorage.getItem(STORAGE_USER_UUID_KEY) || "";
    setCurUserId(storageUserId);
    if (!storageUserId) {
      const toPath = "/movie/login";
      history.push({
        pathname: toPath,
      });
      return;
    }
    const data = {
      userId: storageUserId,
      userName: storageUserName ? storageUserName : undefined,
    };
    setLoading(true);
    Axios.post(API_URL + "/login", data)
      .then((res) => {
        setLoading(false);
        getUserHistoryList(storageUserId);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getUserHistoryList = useCallback((userId) => {
    const tmpUserId = userId ? userId : curUserId;
    if (tmpUserId) {
      const movieListUrl = `${API_URL}/movie/click/${tmpUserId}?curPage=0&pageSize=20`;
      Axios.get(movieListUrl)
        .then((res) => {
          // Hide History if result is empty
          if (res.data && res.data.data && res.data.data.length > 0) {
            setShowHistory(true);
            setHistoryData(res.data.data);
          } else {
            setShowHistory(false);
          }
        })
        .catch((error) => {
          // setLoadingData(false);
          console.error(error);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const goToDashboard = () => {
    history.push("/movie/dashboard");
  };

  return (
    <div>
      <Header />
      <div className="rs-movie-list">
        <div className="breadcrumb">
          <Breadcrumbs aria-label="breadcrumb">
            <Link style={{ color: "#fff" }} color="inherit" href="/#/">
              HOME
            </Link>
            <Typography style={{ color: "#fff" }}>
              Movie Recommender List
            </Typography>
          </Breadcrumbs>
          <div className="dashboard-link">
            {!isMobile && curUserName === RS_ADMIN_USER_NAME && (
              <Button
                className="movie-button"
                variant="outlined"
                size="small"
                onClick={() => {
                  goToDashboard();
                }}
              >
                DashBoard
              </Button>
            )}
            {/* <a className="link" href="/#/news/dashboard">
              仪表盘
            </a> */}
          </div>
        </div>
        {loading ? (
          <div style={{ margin: "20px auto", textAlign: "center" }}>
            <Loader type="ThreeDots" color="#eee" height={50} width={50} />
          </div>
        ) : (
          <div>
            <SlideItem
              type="recommend"
              name="Recommender Movie List"
              movieList={[]}
              clickChange={(item: MovieType, userId: string) => {
                console.info("item:", item);
                if (item) {
                  setShowHistory(true);
                  setHistoryData([item, ...historyData]);
                  portraitRef?.current?.getPortrait();
                }
              }}
            />
            {showHistory && (
              <div className="user-history">
                <div className="history-list">
                  <SlideItem
                    type="user_history"
                    name="Watching History"
                    movieList={historyData}
                    clickChange={(item: MovieType) => {
                      console.info("item:", item);
                    }}
                  />
                </div>
                <div className="user-portrait">
                  <Portrait ref={portraitRef} />
                </div>
              </div>
            )}

            {MOVIE_TYPE_LIST.map((element, index) => {
              return (
                <LazyLoad
                  once={true}
                  key={index}
                  // debounce={500}
                  height={200}
                  offset={10}
                  // placeholder={"<div>Loading ITEM</div>"}
                >
                  <SlideItem
                    movieList={[]}
                    name={element.name}
                    type={element.value}
                    clickChange={(item: MovieType, userId: string) => {
                      console.info("item:", item);
                      if (item) {
                        setShowHistory(true);
                        setHistoryData([item, ...historyData]);
                        portraitRef?.current?.getPortrait();
                      }
                    }}
                  />
                </LazyLoad>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default MovieList;
