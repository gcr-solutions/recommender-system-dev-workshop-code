import React, { useState, useEffect, useCallback, useContext } from "react";
import { useMappedState } from "redux-react-hook";
// Import Swiper React components
import SwiperCore, { Navigation, Pagination, Scrollbar, A11y } from "swiper";
import { Swiper, SwiperSlide } from "swiper/react";
import PlayCircleOutlineIcon from "@material-ui/icons/PlayCircleOutline";
import ThumbUpAltIcon from "@material-ui/icons/ThumbUpAlt";
import ThumbDownAltIcon from "@material-ui/icons/ThumbDownAlt";
// import AddCircleOutlineIcon from "@material-ui/icons/AddCircleOutline";
import FavoriteBorderIcon from "@material-ui/icons/FavoriteBorder";
import FavoriteIcon from "@material-ui/icons/Favorite";

import Refresh from "@material-ui/icons/Refresh";
// import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import StarIcon from "@material-ui/icons/Star";
import QueryBuilderIcon from "@material-ui/icons/QueryBuilder";

import Button from "@material-ui/core/Button";
import PlayArrowIcon from "@material-ui/icons/PlayArrow";
import IconButton from "@material-ui/core/IconButton";
import MuiDialogTitle from "@material-ui/core/DialogTitle";
import CloseIcon from "@material-ui/icons/Close";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import Typography from "@material-ui/core/Typography";

import Loader from "react-loader-spinner";
import Axios from "assets/utils/http";
import LazyLoad from "react-lazyload";

import { AppConfigType, MovieType } from "common/types";
import AppConfigContext from "common/AppConfigContext";

import { IState } from "store/Store";

import Rate from "rc-rate";
import "rc-rate/assets/index.css";

// Import Swiper styles
import "swiper/swiper.scss";
import "swiper/components/navigation/navigation.scss";
import "swiper/components/pagination/pagination.scss";
import "swiper/components/scrollbar/scrollbar.scss";
import { ENUM_NEWS_TYPE, STORAGE_USER_UUID_KEY } from "common/config/const";
// import { SpaOutlined } from "@material-ui/icons";

// install Swiper modules
SwiperCore.use([Navigation, Pagination, Scrollbar, A11y]);

type SlideItemProp = {
  name: string;
  type?: string;
  clickChange: any;
  setShowHistory?: any;
  movieList: MovieType[];
};

const mapState = (state: IState) => ({
  curUser: state.curUser,
});

const SlideItem: React.FC<SlideItemProp> = (props: SlideItemProp) => {
  const { name, type, clickChange, movieList } = props;
  // const shuffleArrayNew = shuffleArray(MovieListData);
  const [visible, setVisible] = useState(false);
  const [curMovie, setCurMovie] = useState<MovieType | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [movieData, setMovieData] = useState(movieList);
  const [clicking, setClicking] = useState(false);

  const { curUser } = useMappedState(mapState);

  const appConfig: AppConfigType = useContext(
    AppConfigContext
  ) as AppConfigType;
  const API_URL = appConfig.MOVIE_API_URL;

  const userUuid =
    curUser?.userId || localStorage.getItem(STORAGE_USER_UUID_KEY);

  let movieListUrl = `${API_URL}/movie?type=${type}&userId=${userUuid}&curPage=0&pageSize=10`;

  const getMovieListByType = useCallback(() => {
    setMovieData([]);
    if (type !== "user_history") {
      setLoadingData(true);
      Axios.get(movieListUrl)
        .then((res) => {
          setLoadingData(false);
          console.info("res:", res);
          setMovieData(res.data.data);
        })
        .catch((error) => {
          setLoadingData(false);
          console.error(error);
        });
    } else {
      setMovieData(movieList);
    }
    // aeslint-disable-next-line react-hooks/exhaustive-deps
  }, [movieList, movieListUrl, type]);

  useEffect(() => {
    getMovieListByType();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type]);

  useEffect(() => {
    if (type === "user_history") {
      setMovieData(movieList);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [movieList]);

  const showMovieDetail = (item: MovieType) => {
    setVisible(true);
    const data = {
      userId: userUuid,
      itemId: item.id,
    };
    if (!clicking) {
      setClicking(true);
      Axios.post(`${API_URL}/click`, data)
        .then((res) => {
          setCurMovie(item);
          setClicking(false);
        })
        .catch((err) => {
          setClicking(false);
          console.error(err);
        });
    }
  };

  // Monitor Cur Movie Change
  useEffect(() => {
    clickChange(curMovie, userUuid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [curMovie]);

  return (
    <LazyLoad once={true}>
      <div className="movie-item">
        <div
          className="item-title"
          style={{ marginBottom: type === "recommend" ? 7 : 0 }}
        >
          {type === "recommend" && (
            <span>
              <StarIcon />
            </span>
          )}
          {type === "user_history" && (
            <span>
              <QueryBuilderIcon />
            </span>
          )}
          {name}
          {type !== "user_history" && (
            <Button
              onClick={() => {
                getMovieListByType();
              }}
              startIcon={<Refresh />}
              className="movie-button"
              size="small"
              // variant="outlined"
            >
              Refresh
            </Button>
          )}
        </div>
        {/* <div>{JSON.stringify(movieData) || "nono"}</div> */}
        <div className="item-slide">
          {loadingData ? (
            <div style={{ margin: "40px auto", textAlign: "center" }}>
              <Loader type="ThreeDots" color="#eee" height={50} width={50} />
            </div>
          ) : (
            <Swiper
              // spaceBetween={0}
              // slidesPerView={8}
              // zoom={{
              //   maxRatio: 1.2,
              //   // minRation: 1,
              // }}
              // zoom
              navigation
              breakpoints={{
                100: {
                  slidesPerView: 3,
                  // spaceBetween: 10
                },
                640: {
                  slidesPerView: 3,
                  // spaceBetween: 0,
                },
                768: {
                  slidesPerView: 4,
                  // spaceBetween: 10,
                },
                1024: {
                  slidesPerView: type === "user_history" ? 5 : 8,
                  // spaceBetween: 10,
                },
              }}
              // pagination={{ clickable: true }}
              // scrollbar={{ draggable: true }}
              onSwiper={(swiper) => console.log(swiper)}
              onSlideChange={() => console.log("slide change")}
            >
              {movieData.map((element: MovieType, index: number) => {
                return (
                  <SwiperSlide className="swiper-slide" key={index}>
                    <div
                      onClick={(event) => {
                        showMovieDetail(element);
                      }}
                      className="image"
                    >
                      <img src={`${element.image}`} alt="element" />
                      {element.tag?.[0] === ENUM_NEWS_TYPE.COLDSTART &&
                        type === ENUM_NEWS_TYPE.RECOMMEND && (
                          <span className="flag-icon cold-start">
                            Cold Start
                          </span>
                        )}
                      {element.tag?.[0] === ENUM_NEWS_TYPE.RECOMMEND &&
                        type === ENUM_NEWS_TYPE.RECOMMEND && (
                          <span className="flag-icon recommand">Recommend</span>
                        )}
                      {element.tag?.[0] === ENUM_NEWS_TYPE.DIVERSITY &&
                        type === ENUM_NEWS_TYPE.RECOMMEND && (
                          <span className="flag-icon diversity">Diversify</span>
                        )}
                      <div className="info">
                        <div className="title">{element.title}</div>
                        <div className="buttons">
                          <span
                            onClick={(event) => {
                              event.stopPropagation();
                              event.preventDefault();
                            }}
                          >
                            <PlayCircleOutlineIcon />
                          </span>
                          <span
                            onClick={(event) => {
                              event.stopPropagation();
                              event.preventDefault();
                            }}
                          >
                            {element.liked ? (
                              <FavoriteIcon />
                            ) : (
                              <FavoriteBorderIcon
                                onClick={() => {
                                  console.info("LIKE");
                                  setMovieData((prevData) => {
                                    // prevData?.[index]?.liked = true;
                                    const jsonData: any = JSON.parse(
                                      JSON.stringify(prevData)
                                    );
                                    jsonData[index].liked = true;
                                    console.info("jsonData:", jsonData);
                                    return jsonData;
                                  });
                                }}
                              />
                            )}
                          </span>
                          <span
                            onClick={(event) => {
                              event.stopPropagation();
                              event.preventDefault();
                            }}
                          >
                            <ThumbUpAltIcon />
                          </span>
                          <span
                            onClick={(event) => {
                              event.stopPropagation();
                              event.preventDefault();
                            }}
                          >
                            <ThumbDownAltIcon />
                          </span>
                          {/* <span className="help">
                          <HelpOutlineIcon />
                        </span> */}
                        </div>
                      </div>
                    </div>
                  </SwiperSlide>
                );
              })}
            </Swiper>
          )}
        </div>
        <Dialog
          open={visible}
          onClose={() => setVisible(false)}
          fullWidth={true}
          maxWidth="md"
          // scroll="body"
          aria-labelledby="alert-dialog-title"
          aria-describedby="alert-dialog-description"
          PaperProps={{
            style: {
              marginTop: 100,
              backgroundColor: "#141414",
              // backgroundImage: `url(${curMovie?.image})`,
              backgroundSize: "cover",
              backgroundPosition: "50px center",
              boxShadow: "none",
            },
          }}
        >
          <MuiDialogTitle disableTypography>
            <Typography
              style={{ paddingRight: "50px", color: "#fff" }}
              variant="h6"
            >
              <b>{curMovie?.title}</b>
            </Typography>
            <IconButton
              onClick={() => {
                setVisible(false);
              }}
              style={{
                position: "absolute",
                color: "#fff",
                right: "10px",
                top: "5px",
              }}
              aria-label="close"
            >
              <CloseIcon />
            </IconButton>
          </MuiDialogTitle>
          <DialogContent>
            <div
              className="big-pic-bg"
              style={{ backgroundImage: `url(${curMovie?.image})` }}
            >
              <div className="buttons">
                <span>
                  <Button
                    variant="contained"
                    color="primary"
                    // className={classes.button}
                    startIcon={<PlayArrowIcon />}
                  >
                    Play
                  </Button>
                </span>

                <span
                  className="icon"
                  onClick={(event) => {
                    event.stopPropagation();
                    event.preventDefault();
                  }}
                >
                  <FavoriteBorderIcon fontSize="large" />
                </span>
                <span
                  className="icon"
                  onClick={(event) => {
                    event.stopPropagation();
                    event.preventDefault();
                  }}
                >
                  <ThumbUpAltIcon fontSize="large" />
                </span>
                <span
                  className="icon"
                  onClick={(event) => {
                    event.stopPropagation();
                    event.preventDefault();
                  }}
                >
                  <ThumbDownAltIcon fontSize="large" />
                </span>
              </div>
            </div>
            <div className="dialog-content">
              <div className="rs-desc">
                <div className="normal">
                  <div className="time">
                    Release time: <b>{curMovie?.release_year}</b>
                  </div>
                  <div className="time">
                    Duration: <b>1h 26m</b>
                  </div>
                  <div className="desc">{curMovie?.desc}</div>
                </div>
                <div className="type">
                  <div className="type-content">
                    <div className="rate text-right">
                      <Rate />
                    </div>
                    <div className="type-item">
                      <label>Director:</label> {curMovie?.director}
                    </div>
                    <div className="type-item">
                      <label>Actors:</label>{" "}
                      {curMovie?.actor.split("|").join(", ")}
                    </div>
                    <div className="type-item">
                      <label>Type:</label>{" "}
                      {curMovie?.category_property.split("|").join(", ")}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </LazyLoad>
  );
};

export default SlideItem;
