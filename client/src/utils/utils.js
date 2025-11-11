/**
 * check to see if input string is a json string
 * @param {*} str
 * @return {bool} true if input string is a json string and false otherwise.
 */
export function isJson(str) {
  try {
    JSON.parse(str);
  } catch (e) {
    return false;
  }
  return true;
}


/**
 *
 * @param {*} lower - starting value
 * @param {*} upper - ending value
 * @return {*} integer array from starting value to ending value
 */
export function createArray(lower, upper) {
  const result = [];

  for (let i=lower; i<=upper; i++) {
    result.push(i);
  }

  return result;
}

/**
 *
 * @return {object} - default headers for fetch request
 */
export function getDefaultHeaders() {
  return {
    headers: {
      'Content-Type': 'application/json',
    },
  };
};

/**
 * @param {*} response - fetch response object
 * @param {*} successHandler - function to call on success
 * @param {*} failHandler - function to call on failure
 * @return {object} - fetch response object
 */
export function handleResponse(response, successHandler, failHandler) {
  if (response.ok) {
    return response.json()
        .then((data) => {
          successHandler(data);
        });
  } else {
    return response.text()
        .then((data) => {
          failHandler(data);
        });
  }
}

/**
 * @param {*} data - response data
 * @return {void} - alert user with error message
 */
export function handleError(data) {
  if (!isJson(data)) {
    alert(data);
    return;
  }
  const jsonData = JSON.parse(data);

  if (jsonData && jsonData.message) {
    alert(jsonData.message);
  }
}
