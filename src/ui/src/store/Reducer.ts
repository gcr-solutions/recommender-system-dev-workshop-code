import { Action, IState } from "./Store";

const reducer = (
  state: IState | null | undefined,
  action: Action
): IState | null => {
  if (!state) {
    return null;
  }

  switch (action.type) {
    case "set current user": {
      return {
        ...state,
        curUser: action.curUser,
      };
    }
    case "set current page": {
      return {
        ...state,
        curPage: action.curPage,
      };
    }

    default:
      return state;
  }
};

export default reducer;
