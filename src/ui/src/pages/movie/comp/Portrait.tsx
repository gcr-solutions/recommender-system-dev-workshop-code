import React, {
  useState,
  useEffect,
  forwardRef,
  useCallback,
  useContext,
  useImperativeHandle,
} from "react";
import { useMappedState } from "redux-react-hook";
// Import Swiper React components
import ReactWordcloud, { OptionsProp, Word } from "react-wordcloud";
import { Resizable } from "re-resizable";
import randomColor from "randomcolor"; // import the script
import SentimentVerySatisfiedIcon from "@material-ui/icons/SentimentVerySatisfied";
import useWindowSize from "hooks/useWindowSize";

// import FaceIcon from "@material-ui/icons/Face";
import Axios from "assets/utils/http";

import { AppConfigType } from "common/types";
import AppConfigContext from "common/AppConfigContext";

import { IState } from "store/Store";

import { STORAGE_USER_UUID_KEY } from "common/config/const";

import "tippy.js/dist/tippy.css";
import "tippy.js/animations/scale.css";

const mapState = (state: IState) => ({
  curUser: state.curUser,
});

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

const Portrait = (props: any, ref: any) => {
  console.info("props:", props);
  const size = useWindowSize();
  // const { name, type } = props;
  const [loadingData, setLoadingData] = useState(false);
  const [cloudWordWidth, setCloudWordWidth] = useState(300);
  const [cloudWordHeight, setCloudWordHeight] = useState(130);

  const { curUser } = useMappedState(mapState);
  const [portraitWords, setPortraitWords] = useState<Word[]>([]);

  const appConfig: AppConfigType = useContext(
    AppConfigContext
  ) as AppConfigType;
  const API_URL = appConfig.MOVIE_API_URL;
  console.info("appConfig:", appConfig);

  const userUuid =
    curUser?.userId || localStorage.getItem(STORAGE_USER_UUID_KEY);

  const callbacks = {
    getWordColor: (word: Word) =>
      word.type === "ITEM" ? "#fff" : randomColor({ luminosity: "light" }),
    onWordClick: console.log,
    onWordMouseOver: console.log,
    getWordTooltip: (word: Word) => `兴趣度:${word.value.toFixed(5)}`,
  };

  useEffect(() => {
    setCloudWordWidth(
      size.width > 768 ? Math.floor(size.width * 0.35) : size.width - 50
    );
    setCloudWordHeight(Math.floor(size.height * 0.3));
  }, [size]);

  const getUserPortrait = useCallback(() => {
    setLoadingData(true);
    Axios.get(`${API_URL}/portrait/userid/${userUuid}`)
      .then((res) => {
        setLoadingData(false);
        console.info("user portrait res:", res);
        console.info("portrait:res:", res);
        if (res.data && res.data.data) {
          const portraitData = res.data.data;
          const portraitArr = Object.keys(portraitData);
          console.info("portraitArr:", portraitArr);
          const tmpPortraitArr: Word[] = [];
          const typeArr = portraitData.category;
          const actorArr = portraitData.actor;
          const directorArr = portraitData.director;
          console.info("typeArr:", typeArr);
          console.info("actorArr:", actorArr);
          const typeScoreArr = [];
          if (typeArr) {
            for (let type in typeArr) {
              const typeObj = typeArr[type];
              if (type !== "recent") {
                typeScoreArr.push(typeObj.score);
                tmpPortraitArr.push({
                  text: type,
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
            if (actorArr) {
              for (let actor in actorArr) {
                const typeObj = actorArr[actor];
                const refScore = typeObj <= typeAvg ? typeObj : typeAvg;
                if (actor !== "recent" && actor.length < 15) {
                  tmpPortraitArr.push({
                    text: actor,
                    value: refScore - 0.3 > 0 ? refScore - 0.3 : 0.0001,
                    type: "ITEM",
                  });
                }
              }
            }
            if (directorArr) {
              for (let director in directorArr) {
                const directorObj = directorArr[director];
                const refScore = directorObj <= typeAvg ? directorObj : typeAvg;
                if (director !== "recent" && director.length < 15) {
                  tmpPortraitArr.push({
                    text: director,
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
      .catch((error) => {
        setLoadingData(false);
        console.error(error);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useImperativeHandle(ref, () => ({
    getPortrait() {
      getUserPortrait();
    },
  }));

  useEffect(() => {
    getUserPortrait();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loadingData) {
    return <div>Loading</div>;
  }

  return (
    <div>
      <div className="item-title">
        <span>
          <SentimentVerySatisfiedIcon />
        </span>
        User Portrait
      </div>
      <div className="word-cloud">
        <Resizable
          defaultSize={{
            width: cloudWordWidth,
            height: cloudWordHeight,
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
      </div>
    </div>
  );
};

export default forwardRef(Portrait);
