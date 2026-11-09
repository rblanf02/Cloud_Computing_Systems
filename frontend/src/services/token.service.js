const TOKEN_KEY = "cloudfile_access_token";
const USER_KEY = "cloudfile_user";

const tokenService = {
  getLocalAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  saveAccessToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  saveUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  getUser() {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  },
  removeSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export default tokenService;
