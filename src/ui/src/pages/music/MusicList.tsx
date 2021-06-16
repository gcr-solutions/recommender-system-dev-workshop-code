import React, { useEffect } from "react";
import { useDispatch } from "redux-react-hook";
import Header from "common/Header";

const MusicList: React.FC = () => {
  const dispatch = useDispatch();
  useEffect(() => {
    dispatch({ type: "set current page", curPage: "MUSIC" });
  }, [dispatch]);
  return (
    <div>
      <Header />
      <div className="comming-soon">Music Comming Soon</div>
    </div>
  );
};

export default MusicList;
