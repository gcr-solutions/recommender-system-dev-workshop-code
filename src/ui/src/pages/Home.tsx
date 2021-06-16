import React, { useEffect } from "react";
import AppConfigContext from "common/AppConfigContext";
import { useHistory } from "react-router-dom";
import { AppConfigType, ENUM_DEPLOY_TYPE } from "common/types";
import DataLoading from "common/Loading";

// loading component for suspense fallback
const Loader = () => (
  <div className="App">
    <div className="app-loading">
      <DataLoading />
      AWS Recommendation System is loading...
    </div>
  </div>
);

const Home: React.FC = () => {
  const history = useHistory();

  const appConfig: AppConfigType = React.useContext(
    AppConfigContext
  ) as AppConfigType;
  const deployType = appConfig.DEPLOY_TYPE;

  useEffect(() => {
    console.info("AAAA");
    let toPath = "/";
    if (
      deployType === ENUM_DEPLOY_TYPE.NEWS ||
      deployType === ENUM_DEPLOY_TYPE.ALL
    ) {
      console.info("NEWS");
      // Show News Login First
      toPath = "/news/login";
    } else {
      console.info("MOVIE");
      // Show Movie Login
      toPath = "/movie/login";
    }
    history.push({
      pathname: toPath,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <Loader />
    </div>
  );
};

export default Home;
