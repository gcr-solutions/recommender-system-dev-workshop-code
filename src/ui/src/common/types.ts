export interface AppConfigType {
  DEPLOY_TYPE: string;
  NEWS_API_URL: string;
  MOVIE_API_URL: string;
}

export type MovieType = {
  id: string;
  image: string;
  title: string;
  release_year: string;
  director: string;
  actor: string;
  category_property: string;
  new_series: string;
  level: string;
  desc: string;
  type: string;
  tag: string[];
  liked?: boolean;
};

export enum ENUM_DEPLOY_TYPE {
  NEWS = "NEWS",
  MOVIE = "MOVIE",
  ALL = "ALL",
}

export const MOVIE_TYPE_LIST = [
  { name: "Action", value: "action" },
  { name: "Adventure", value: "adventure" },
  { name: "Fantasy", value: "fantasy" },
  { name: "Thriller", value: "thriller" },
  { name: "Drama", value: "drama" },
  { name: "Crime", value: "crime" },
  { name: "Comedy", value: "comedy" },
  { name: "Family", value: "family" },
  { name: "Romance", value: "romance" },
  { name: "Mystery", value: "mystery" },
];
