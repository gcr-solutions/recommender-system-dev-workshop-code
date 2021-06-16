import { createStore } from "redux";
import reducer from "./Reducer";

interface UserInfo {
  userId: string;
  visitCount: number;
  userName: string;
}
export interface IState {
  curUser: UserInfo | null;
  curPage: string;
  todos: string[];
}

export type Action =
  | {
      type: "set current user";
      curUser: UserInfo;
    }
  | {
      type: "set current page";
      curPage: string;
    };

export function makeStore(): unknown {
  return createStore(reducer, {
    curUser: null,
    curPage: "",
    todos: [],
  });
}
