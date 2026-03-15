class BaseModule {
  /**
   * Process the input data and return output data.
   * @param {any} input - Input data (could be a stream, buffer, etc.)
   * @param {Object} config - Configuration for this module
   * @returns {Promise<any>} - Output data
   */
  async process(input, config) {
    throw new Error('Method process() must be implemented');
  }
}

module.exports = BaseModule;