import React, { useState, useEffect } from "react";
import Chart from "react-apexcharts";
import useWindowSize from "hooks/useWindowSize";

export interface BarChartProps {
  foreColor?: string;
  chartTheme?: string;
  chartData: {
    categoryList: string[];
    clickCountList: number[];
  };
}

const CategoryBarChart: React.FC<BarChartProps> = (props) => {
  const size = useWindowSize();
  const { foreColor, chartTheme, chartData } = props;
  console.info("chartData:", chartData);
  console.info("chartData.categoryList:", chartData.categoryList);
  console.info("chartData.clickCountList:", chartData.clickCountList);
  const [chartHeight, setChartHeight] = useState(100);

  useEffect(() => {
    setChartHeight(size.height * 0.25 - 30);
  }, [size]);

  const options = {
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
    xaxis: {
      categories: chartData.categoryList,
    },
    tooltip: {
      theme: chartTheme === "dark" ? "dark" : "light",
    },
    grid: {
      borderColor: chartTheme === "dark" ? "#535A6C" : undefined,
      xaxis: {
        lines: {
          show: chartTheme === "dark" ? true : false,
        },
      },
      padding: {
        // left: 30,
        // bottom: 50,
      },
      row: {
        colors: chartTheme === "dark" ? undefined : ["#f3f3f3", "transparent"], // takes an array which will be repeated on columns
        opacity: 0.5,
      },
    },
  };
  const series = [
    {
      name: chartTheme === "dark" ? "Clicks" : "点击次数",
      data: chartData.clickCountList,
    },
  ];

  return (
    <div className="mixed-chart" style={{ height: chartHeight }}>
      <Chart
        options={options}
        series={series}
        type="bar"
        width="100%"
        height="100%"
      />
    </div>
  );
};

export default CategoryBarChart;
