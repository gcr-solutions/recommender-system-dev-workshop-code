import React, { useState, useEffect, Suspense } from "react";
import { HashRouter, Route } from "react-router-dom";
import axios from "axios";
import {
  createMuiTheme,
  responsiveFontSizes,
  MuiThemeProvider,
  // Typography,
  Theme,
} from "@material-ui/core";

import DataLoading from "./common/Loading";
import AppConfigContext from "./common/AppConfigContext";

import Home from "./pages/Home";
import Login from "./pages/login/Login";
import NewsList from "./pages/news/NewsList";
import MovieList from "./pages/movie/MovieList";
import MusicList from "./pages/music/MusicList";

import NewsDashboard from "./pages/dashboard/NewsDashboard";
import MovieDashboard from "./pages/dashboard/MovieDashboard";

import "./index.scss";

let theme: Theme = createMuiTheme();
theme = responsiveFontSizes(theme);

// loading component for suspense fallback
const Loader = () => (
  <div className="App">
    <div className="app-loading">
      <DataLoading />
      AWS Recommendation System is loading...
    </div>
  </div>
);

const App: React.FC = () => {
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [appConfig, setAppConfig] = useState({});

  useEffect(() => {
    const timeStamp = new Date().getTime();
    setLoadingConfig(true);
    axios.get("/aws-exports.json?timeStamp=" + timeStamp).then((res) => {
      console.info("res:", res);
      setAppConfig(res.data);
      setLoadingConfig(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loadingConfig) {
    return <Loader />;
  }

  return (
    <div>
      <div className="App">
        <MuiThemeProvider theme={theme}>
          <AppConfigContext.Provider value={appConfig}>
            <HashRouter>
              <Route path="/" exact component={Home}></Route>
              <Route path="/:type/login" exact component={Login}></Route>
              <Route path="/news" exact component={NewsList}></Route>
              <Route
                path="/news/dashboard"
                exact
                component={NewsDashboard}
              ></Route>
              <Route
                path="/movie/dashboard"
                exact
                component={MovieDashboard}
              ></Route>
              <Route path="/movie" exact component={MovieList}></Route>
              <Route path="/music" exact component={MusicList}></Route>
            </HashRouter>
          </AppConfigContext.Provider>
        </MuiThemeProvider>
      </div>
    </div>
  );
};

const WithProvider = () => <App />;

// here app catches the suspense from page in case translations are not yet loaded
export default function RouterApp(): JSX.Element {
  return (
    <Suspense fallback={<Loader />}>
      <WithProvider />
    </Suspense>
  );
}
