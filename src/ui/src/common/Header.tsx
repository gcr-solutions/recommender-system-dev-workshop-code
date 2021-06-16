import React, { useState, useEffect } from "react";
import Avatar from "react-avatar";
import { useTranslation } from "react-i18next";
import { useHistory } from "react-router-dom";
import { slide as Menu } from "react-burger-menu";
import useWindowSize from "hooks/useWindowSize";

// import ButtonDropdown from "aws-northstar/components/ButtonDropdown";
import { useMappedState } from "redux-react-hook";
import classNames from "classnames";
import { IState } from "store/Store";
import AppConfigContext from "common/AppConfigContext";

import LOGO from "assets/images/icon.svg";

import {
  STORAGE_USER_NAME_KEY,
  STORAGE_USER_UUID_KEY,
  STORAGE_USER_VISIT_COUNT_KEY,
  VISITOR_ANOMY_ID,
} from "common/config/const";
import { AppConfigType } from "./types";

const mapState = (state: IState) => ({
  curPage: state.curPage,
  curUser: state.curUser,
});

const Header: React.FC = () => {
  const history = useHistory();
  const { curPage, curUser } = useMappedState(mapState);
  const [isMobile, setIsMobile] = useState(false);
  // const [showMenu, setShowMenu] = useState(false);
  const size = useWindowSize();

  const curUserName =
    curUser?.userName || localStorage.getItem(STORAGE_USER_NAME_KEY) || "";
  const visitCount =
    curUser?.userId || localStorage.getItem(STORAGE_USER_VISIT_COUNT_KEY) || 1;
  const appConfig: AppConfigType = React.useContext(
    AppConfigContext
  ) as AppConfigType;
  const goToPage = (pageUrl: string) => {
    history.push({
      pathname: pageUrl,
    });
  };

  const { t, i18n } = useTranslation();

  useEffect(() => {
    console.info("size:", size);
    if (size.width > 768) {
      setIsMobile(false);
    } else {
      setIsMobile(true);
    }
  }, [size]);

  const logout = () => {
    localStorage.removeItem(STORAGE_USER_NAME_KEY);
    localStorage.removeItem(STORAGE_USER_VISIT_COUNT_KEY);
    localStorage.removeItem(STORAGE_USER_UUID_KEY);
    history.push({
      pathname: "/",
    });
  };

  const showSettings = (event: any) => {
    event.preventDefault();
    console.info("event:", event);
  };

  return (
    <div className="top-bar">
      {curPage !== "HOME" && appConfig.DEPLOY_TYPE === "ALL" && (
        <Menu width={"300px"}>
          <div
            id="home"
            className="l-menu-item"
            onClick={() => {
              history.push({
                pathname: "/",
              });
            }}
          >
            {t("menu.home")}
          </div>
          <div
            className={classNames("l-menu-item", {
              active: curPage === "NEWS",
            })}
            onClick={() => {
              history.push({
                pathname: "/news",
              });
            }}
          >
            {t("menu.news")}
          </div>
          <div
            className={classNames("l-menu-item", {
              active: curPage === "MOVIE",
            })}
            onClick={() => {
              history.push({
                pathname: "/movie",
              });
            }}
          >
            {t("menu.movie")}
          </div>
          <span onClick={showSettings} className="l-menu-item">
            {curPage !== "HOME" && (
              <div className="user">
                <span>
                  {(curUser?.userName === VISITOR_ANOMY_ID ||
                    curUserName === VISITOR_ANOMY_ID) && (
                    <span>{t(VISITOR_ANOMY_ID)}</span>
                  )}
                  {curUser?.userName !== VISITOR_ANOMY_ID &&
                    curUserName !== VISITOR_ANOMY_ID && (
                      <span>{curUser?.userName || curUserName}</span>
                    )}
                  (
                  <span
                    className="logout"
                    onClick={() => {
                      logout();
                    }}
                  >
                    {t("logout")}
                  </span>
                  )
                </span>
              </div>
            )}
          </span>
        </Menu>
      )}

      <div
        className="logo"
        style={{
          marginLeft:
            isMobile && curPage !== "HOME" && appConfig.DEPLOY_TYPE === "ALL"
              ? "30px"
              : "0px",
        }}
      >
        <img alt="GCR Solutions" src={LOGO} />
        <span>{t("name")}</span>
      </div>
      {curPage !== "HOME" && !isMobile && appConfig.DEPLOY_TYPE === "ALL" && (
        <div
          className={classNames("menu-bar", {
            long: i18n.language === "en" || i18n.language === "en-US",
          })}
        >
          <span
            onClick={() => {
              goToPage("/news");
            }}
            className={classNames("menu-item", {
              active: curPage === "NEWS",
            })}
          >
            {t("menu.news")}
          </span>
          <span
            onClick={() => {
              goToPage("/movie");
            }}
            className={classNames("menu-item", {
              active: curPage === "MOVIE",
            })}
          >
            {t("menu.movie")}
          </span>
          {/* <span
            onClick={() => {
              goToPage("music");
            }}
            className={classNames("menu-item", {
              active: curPage === "MUSIC",
            })}
          >
            {t("menu.music")}
          </span> */}
        </div>
      )}

      <div className="user-info">
        {curPage !== "HOME" && (
          <Avatar
            round={true}
            size="30"
            color="#f2af4e"
            name={curUser?.userName || curUserName}
          />
        )}
        {curPage !== "HOME" && (
          <div className="user">
            <span>
              {(curUser?.userName === VISITOR_ANOMY_ID ||
                curUserName === VISITOR_ANOMY_ID) && (
                <span>{t(VISITOR_ANOMY_ID)}</span>
              )}
              {curUser?.userName !== VISITOR_ANOMY_ID &&
                curUserName !== VISITOR_ANOMY_ID && (
                  <span>{curUser?.userName || curUserName}</span>
                )}
              (
              <span
                className="logout"
                onClick={() => {
                  logout();
                }}
              >
                {t("logout")}
              </span>
              )
              {curUserName !== VISITOR_ANOMY_ID && (
                <span className="welcome">
                  , {t("header.preTime")}
                  {curUser?.visitCount || visitCount}
                  {i18n.language === "en" &&
                    (visitCount as number) % 10 === 1 &&
                    t("header.time1")}
                  {i18n.language === "en" &&
                    (visitCount as number) % 10 === 2 &&
                    t("header.time2")}
                  {i18n.language === "en" &&
                    (visitCount as number) % 10 === 3 &&
                    t("header.time3")}
                  {i18n.language === "en" &&
                    (visitCount as number) % 10 !== 1 &&
                    (visitCount as number) % 10 !== 2 &&
                    (visitCount as number) % 10 !== 3 &&
                    t("header.time0")}
                  {t("header.visit")}
                </span>
              )}
            </span>
          </div>
        )}
      </div>

      <div className="user-info-mobile">
        {curPage !== "HOME" && (
          <Avatar
            round={true}
            size="30"
            color="#f2af4e"
            name={curUser?.userName || curUserName}
          />
        )}
        {curPage !== "HOME" && (
          <div className="user">
            <span>
              {curUser?.userName || curUserName}(
              <span
                className="logout"
                onClick={() => {
                  logout();
                }}
              >
                退出
              </span>
              )
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default Header;
