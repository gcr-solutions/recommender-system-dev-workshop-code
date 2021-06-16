import React, { useState, useEffect } from "react";
import Chart from "react-apexcharts";
import useWindowSize from "hooks/useWindowSize";

export interface LineChartProps {
  foreColor?: string;
  chartTheme?: string;
  lineChartData: {
    timeCategoryList: string[];
    normalCLickName: string;
    normalClickList: number[];
    recommendClickName: string;
    recommendClickList: number[];
  };
}

const ClickLineChart: React.FC<LineChartProps> = (props) => {
  // const categoryList: string[] = [];
  // DATE_LIST.forEach((element) => {
  //   categoryList.push(element);
  // });
  const size = useWindowSize();
  const [chartHeight, setChartHeight] = useState(200);

  useEffect(() => {
    setChartHeight(size.height * 0.5 - 0);
  }, [size]);

  const { foreColor, chartTheme, lineChartData } = props;

  const options = {
    id: "basic-bar",
    type: "line",
    chart: {
      theme: {
        mode: chartTheme,
      },
      foreColor: foreColor,
      toolbar: {
        tools: {
          download: false,
          selection: false,
          zoom: false,
          zoomin: false,
          zoomout: false,
          pan: false,
        },
      },
    },
    animations: {
      enabled: true,
      easing: "linear",
      dynamicAnimation: {
        speed: 1000,
      },
    },
    // zoom: {
    //   enabled: false,
    // },
    // chart: {

    // },
    // stroke: {
    //   width: 3,
    // },
    dataLabels: {
      enabled: false,
    },
    tooltip: {
      theme: chartTheme === "dark" ? "dark" : "light",
    },
    xaxis: {
      categories: lineChartData.timeCategoryList,
    },
    grid: {
      borderColor: chartTheme === "dark" ? "#535A6C" : undefined,
      xaxis: {
        lines: {
          show: chartTheme === "dark" ? true : false,
        },
      },
      padding: {
        // top: 10,
        // left: 30,
        bottom: 0,
      },
      row: {
        colors: chartTheme === "dark" ? undefined : ["#f3f3f3", "transparent"], // takes an array which will be repeated on columns
        opacity: 0.5,
      },
    },
  };
  const series = [
    {
      name: lineChartData.normalCLickName,
      data: lineChartData.normalClickList,
    },
    {
      color: "#f58559",
      name: lineChartData.recommendClickName,
      data: lineChartData.recommendClickList,
    },
  ];

  return (
    <div className="mixed-chart" style={{ height: chartHeight }}>
      <Chart options={options} series={series} width="100%" height="100%" />
    </div>
  );
};

export default ClickLineChart;
