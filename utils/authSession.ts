let currentAccessToken: string | null = null;

export const setCurrentAccessToken = (accessToken: string | null | undefined) => {
  if (typeof window === 'undefined') return;
  currentAccessToken = accessToken || null;
};

export const getCurrentAccessToken = () => {
  if (typeof window === 'undefined') return null;
  return currentAccessToken;
};
