export const USER_ID_NAME = "APP_RECOMMENER_USERID";
// export const API_URL =
//   "https://7y65j8tz9j.execute-api.cn-north-1.amazonaws.com.cn/prod";
export const API_URL = "";
// export const API_URL =
// "http://a6500b130ef7c45eb96f1727f55bafb6-1149103410.ap-southeast-1.elb.amazonaws.com";

export const IMAGE_PATH = "http://r.m.solutions.aws.a2z.org.cn/images/";

export const STORAGE_USER_UUID_KEY = "__RECOMMENDATION_SYS_USER_UUID__";
export const STORAGE_USER_NAME_KEY = "__RECOMMENDATION_SYS_USER_NAME__";
export const STORAGE_USER_VISIT_COUNT_KEY =
  "__RECOMMENDATION_SYS_USER_VISIT_COUNT__";

// CONTENT/MODEL/ACTION
export const STORAGE_CONTENT_ARN_ID =
  "__RECOMMENDATION_SYS_STORAGE_CONTENT_ARN_ID__";

export const STORAGE_MODEL_ARN_ID =
  "__RECOMMENDATION_SYS_STORAGE_MODEL_ARN_ID__";

export const STORAGE_ACTION_ARN_ID =
  "__RECOMMENDATION_SYS_STORAGE_ACTION_ARN_ID__";

// CONTENT/MODEL/ACTION
export const STORAGE_CONTENT_ARN_URL =
  "__RECOMMENDATION_SYS_STORAGE_CONTENT_ARN_URL__";

export const STORAGE_MODEL_ARN_URL =
  "__RECOMMENDATION_SYS_STORAGE_MODEL_ARN_URL__";

export const STORAGE_ACTION_ARN_URL =
  "__RECOMMENDATION_SYS_STORAGE_ACTION_ARN_URL__";

export const VISITOR_ANOMY_ID = "Vrec-anomy-user-xxx";

export const RS_ADMIN_USER_NAME = "gcr-rs-admin";

export enum ENUM_SETTING_TYPE {
  CONTENT = "CONTENT",
  MODEL = "MODEL",
  ACTION = "ACTION",
}

export enum ENUM_NEWS_TYPE {
  RECOMMEND = "recommend",
  DIVERSITY = "diversity",
  COLDSTART = "coldstart",
}

export const PORTRAIT_TYPE_SCORE = 0;
export const PORTRAIT_ITEM_THRESHOLD_SCORE = 0;

export const ROLE_LIST = [
  { label: "学术/教育者", value: "academic/educator" },
  { label: "艺术家", value: "artist" },
  { label: "文书/管理员", value: "clerical/admin" },
  { label: "大学生/毕业生", value: "college/grad student" },
  { label: "客户服务", value: "customer service" },
  { label: "医生/卫生保健", value: "doctor/health care" },
  { label: "行政/管理", value: "executive/managerial" },
  { label: "农民", value: "farmer" },
  { label: "家庭主妇", value: "homemaker" },
  { label: "K-12学生", value: "K-12 student" },
  { label: "律师", value: "lawyer" },
  { label: "程序员", value: "programmer" },
  { label: "退休人员", value: "retired" },
  { label: "销售与市场营销", value: "sales/marketing" },
  { label: "科学家", value: "scientist" },
  { label: "自由职业", value: "self-employed" },
  { label: "技术员/工程师", value: "technician/engineer" },
  { label: "匠人/工匠", value: "tradesman/craftsman" },
  { label: "待业", value: "unemployed" },
  { label: "作家", value: "writer" },
  { label: "其他", value: "other or not specified" },
];

export const HOBBY_LIST = [
  { id: 999, name: "推荐", value: ENUM_NEWS_TYPE.RECOMMEND },
  { id: 100, name: "故事", value: "news_story" },
  { id: 101, name: "文化", value: "news_culture" },
  { id: 102, name: "娱乐", value: "news_entertainment" },
  { id: 103, name: "体育", value: "news_sports" },
  { id: 104, name: "财经", value: "news_finance" },
  { id: 106, name: "房产", value: "news_house" },
  { id: 107, name: "汽车", value: "news_car" },
  { id: 108, name: "教育", value: "news_edu" },
  { id: 109, name: "科技", value: "news_tech" },
  { id: 110, name: "军事", value: "news_military" },
  { id: 112, name: "旅游", value: "news_travel" },
  { id: 113, name: "国际", value: "news_world" },
  { id: 114, name: "股票", value: "stock" },
  { id: 115, name: "三农", value: "news_agriculture" },
  { id: 116, name: "游戏", value: "news_game" },
];

type HobboyType = {
  id: number;
  name: string;
  value: string;
};

interface OjbectType {
  [key: string]: HobboyType;
}

export const converListToMap = () => {
  const tmpObj: OjbectType = {};
  HOBBY_LIST.forEach((element, index) => {
    tmpObj[element.value] = element;
  });
  return tmpObj;
};

export const DATE_LIST = [
  "01-12 00:00",
  "01-12 01:00",
  "01-12 02:00",
  "01-12 03:00",
  "01-12 04:00",
  "01-12 05:00",
  "01-12 06:00",
  "01-12 07:00",
  "01-12 08:00",
  "01-12 09:00",
  "01-12 10:00",
  "01-12 11:00",
  "01-12 12:00",
  "01-12 13:00",
  "01-12 14:00",
  "01-12 15:00",
  "01-12 16:00",
];
