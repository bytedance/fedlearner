export const post = () => ({
  data: {
    data: { success: Math.random() < 0.6, details: [] },
  },
  status: 200,
});
