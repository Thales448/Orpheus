// helpers.js
function getPaginationParams(req) {
  let page = parseInt(req.query.page) || 1;
  let limit = parseInt(req.query.limit) || 100;
  if (limit > 1000) limit = 1000; // Hard cap
  const offset = (page - 1) * limit;
  return { limit, offset, page };
}
module.exports = { getPaginationParams };
