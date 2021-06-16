import Mock, { Random } from "mockjs";

Mock.mock("/api/click", "get", {
  success: true,
  message: "操作成功",
});

Mock.mock("/api/newslist", "get", {
  success: true,
  message: "@cparagraph",
  // 属性 list 的值是一个数组，其中含有 1 到 5 个元素
  "list|8-15": [
    {
      image: Random.image("100x100"),
      title: "@csentence(15, 35)",
      desc: "@cparagraph(2,4)",
      "type|1": [0, 1],
      "tag|1": [
        "推荐",
        "故事",
        "文化",
        "娱乐",
        "体育",
        "财经",
        "房产",
        "汽车",
        "教育",
        "科技",
        "军事",
        "旅游",
        "国际",
        "股票",
        "三农",
        "游戏",
      ],
      // 属性 sid 是一个自增数，起始值为 1，每次增 1
      "sid|+1": 1,
      // 属性 userId 是一个5位的随机码
      "userId|5": "",
    },
  ],
});
