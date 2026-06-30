Page({
  data: {
    historyList: [],
    totalCount: 0,
    absentCount: 0,
  },

  onShow() {
    this.loadData();
  },

  // 加载数据
  loadData() {
    const list = wx.getStorageSync("signRecordList") || [];
    const total = list.reduce((sum, item) => sum + item.actual, 0);
    const absent = list.reduce((sum, item) => sum + item.absent, 0);
    this.setData({
      historyList: list,
      totalCount: total,
      absentCount: absent,
    });
  },

  // 删除单条（带确认）
  deleteItem(e) {
    const targetTime = e.currentTarget.dataset.t;
    const that = this;
    wx.showModal({
      title: "删除确认",
      content: "确定要删除这条签到记录吗？",
      confirmColor: "#F87272",
      confirmText: "删除",
      success(res) {
        if (res.confirm) {
          const newList = that.data.historyList.filter(
            (item) => item.time !== targetTime
          );
          that.setData({ historyList: newList });
          wx.setStorageSync("signRecordList", newList);
          // 刷新统计
          that.loadData();
          wx.showToast({
            title: "已删除",
            icon: "success",
            duration: 1500,
          });
        }
      },
    });
  },

  // 清空全部（带确认）
  clearAll() {
    const that = this;
    wx.showModal({
      title: "清空所有记录",
      content: "确定要清空所有签到记录吗？此操作不可恢复。",
      confirmColor: "#F87272",
      confirmText: "全部清空",
      cancelText: "取消",
      success(res) {
        if (res.confirm) {
          that.setData({
            historyList: [],
            totalCount: 0,
            absentCount: 0,
          });
          wx.setStorageSync("signRecordList", []);
          wx.showToast({
            title: "已清空",
            icon: "success",
            duration: 1500,
          });
        }
      },
    });
  },

  // 预览历史图片
  previewHistoryImage(e) {
    const imgBase64 = e.currentTarget.dataset.img;
    if (!imgBase64) return;

    wx.showLoading({ title: "加载中..." });
    const fs = wx.getFileSystemManager();
    const timestamp = Date.now();
    const savedPath = wx.env.USER_DATA_PATH + "/hist_" + timestamp + ".jpg";

    fs.writeFile({
      filePath: savedPath,
      data: imgBase64.replace(/^data:image\/\w+;base64,/, ""),
      encoding: "base64",
      success() {
        wx.hideLoading();
        wx.previewImage({
          urls: [savedPath],
          current: savedPath,
        });
      },
      fail() {
        wx.hideLoading();
        wx.showToast({ title: "预览失败", icon: "none" });
      },
    });
  },
});
