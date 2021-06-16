import React from "react";
import { useTranslation } from "react-i18next";

import CheckCircleOutlineIcon from "@material-ui/icons/CheckCircleOutline";
import HighlightOffIcon from "@material-ui/icons/HighlightOff";
import AccessTimeIcon from "@material-ui/icons/AccessTime";

interface TrainStatusProps {
  statusRunning: boolean;
  statusSuccess: boolean;
  statusFailed: boolean;
  arnUrl: string;
}

const TrainStatus: React.FC<TrainStatusProps> = (props) => {
  const { t } = useTranslation();

  const { statusRunning, statusSuccess, statusFailed, arnUrl } = props;
  return (
    <>
      {statusRunning && (
        <span className="item status running">
          <AccessTimeIcon className="status-icon" />
          {t("status.inprogress")}
        </span>
      )}
      {statusSuccess && (
        <span className="item status success">
          <CheckCircleOutlineIcon className="status-icon" />
          {t("status.success")}
        </span>
      )}
      {statusFailed && (
        <span className="item status falied">
          <HighlightOffIcon className="status-icon" />
          {t("status.failed")}
        </span>
      )}
      {arnUrl && (
        <span className="item">
          <a className="link" href={arnUrl} target="_blank" rel="noreferrer">
            {t("detail")}
          </a>
        </span>
      )}
    </>
  );
};

export default TrainStatus;
