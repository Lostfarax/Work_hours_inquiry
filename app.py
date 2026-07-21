import streamlit as st
import pandas as pd
from datetime import datetime

# 页面配置
st.set_page_config(page_title="Work Hours Inquiry", page_icon="⏱️", layout="wide")

st.title("⏱️ Hours verification Portal")
st.caption("Note: This page is only used to verify daily working hours and project details. The data source is dynamically updated with database.")

# 1. Read Excel Data
@st.cache_data(ttl=60)  # 60 seconds refresh
def load_data():
    try:
        df = pd.read_excel("daily_hours_log.xlsx")
        # 确保关键列类型正确
        if "EID" in df.columns:
            df["EID"] = df["EID"].astype(str).str.strip()
        if "PAY PERIOD" in df.columns:
            df["PAY PERIOD"] = pd.to_numeric(df["PAY PERIOD"], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"无法读取 Excel 文件，请确认根目录下存在 '工时明细表.xlsx'，且包含标准列名。错误信息: {e}")
        return None

df = load_data()

if df is not None:
    # 检验必要的列
    required_cols = ["EID", "Worker", "Date", "PAY PERIOD", "BU", "BU Description", "Hours", "Equip ID", "Equip Description"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.warning(f"⚠️ 您的 Excel 文件缺少以下必要列，请先补充列名：{missing_cols}")
        st.info("建议表头格式：[EID] [Worker] [Date] [PAY PERIOD] [BU] [BU Description] [Hours] [Equip ID] [Equip Description]")
    else:
        # 获取最新（当前）的 Payroll 编号
        latest_payroll = int(df["PAY PERIOD"].max())
        
        # --- 侧边栏：查询条件 ---
        st.sidebar.header("🔍 Hours Inquiry")
        
        # 输入工号
        input_emp_id = st.sidebar.text_input("Please enter your Employee ID：", value="").strip()
        
        # 选择 Payroll 编号（默认选择最新的一期）
        all_payrolls = sorted(df["PAY PERIOD"].unique(), reverse=True)
        selected_payroll = st.sidebar.selectbox(
            "Choose Pay Period：", 
            all_payrolls, 
            index=0 if latest_payroll in all_payrolls else 0,
            help="The latest Pay period is displayed by default, but you can switch to view historical periods."
        )
        
        if input_emp_id:
            # 过滤工号数据
            emp_all_df = df[df["EID"] == input_emp_id]
            
            if emp_all_df.empty:
                st.error(f"❌  **{input_emp_id}** not found, please check if the employee ID was entered correctly.")
            else:
                emp_name = emp_all_df["Worker"].iloc[0] if "Worker" in emp_all_df.columns else "Worker"
                st.success(f"Wellcome，**{emp_name}**（EID: {input_emp_id}）")
                
                # 过滤当前选择的 Payroll 编号数据
                emp_payroll_df = emp_all_df[emp_all_df["PAY PERIOD"] == selected_payroll].copy()
                
                # 提示当前是否为最新账期
                if selected_payroll == latest_payroll:
                    st.info(f"📅 Display：**No {selected_payroll}  Pay Period**（Newest）")
                else:
                    st.warning(f"📜 Display：**No {selected_payroll} Pay Period**（History）")
                
                if emp_payroll_df.empty:
                    st.info(f"No {selected_payroll} Pay Period has not your record")
                else:
                    # 计算核心工时指标
                    total_hours = emp_payroll_df["Hours"].sum()
                    work_days = emp_payroll_df["Date"].nunique()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Number of days of attendance this period", f"{work_days} Days")
                    col2.metric("Total working hours for this period", f"{total_hours:.1f} Hours")
                    col3.metric("Current pay period", f"No {selected_payroll} ")
                    
                    st.markdown("---")
                    
                    # 展示每日工时与项目明细（不含薪资）
                    st.subheader(f"📋 No {selected_payroll} Daily hours log")
                    
                    display_cols = ["Date", "BU", "BU Description", "Hours","Eqip ID", "Equip Description"]
                    if "Notes" in emp_payroll_df.columns:
                        display_cols.append("Notes")
                        
                    st.dataframe(
                        emp_payroll_df[display_cols].sort_values(by="Date", ascending=True),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 可视化柱状图（每日工时分布）
                    st.subheader("📊 Daily working hours distribution")
                    st.bar_chart(data=emp_payroll_df, x="Date", y="Hours")
                    
                    st.markdown("---")
                    
                    # --- 工时核对与异常反馈区域 ---
                    st.subheader("💬 Feedback on abnormal working hours")
                    st.caption("If you have any objections or omissions regarding the above work hour statistics (such as uncounted work hours, project discrepancies, etc.), please submit feedback below.")
                    
                    with st.form(key="feedback_form", clear_on_submit=True):
                        # feedback_date = st.text_input("有问题的日期（例如：2026-07-15）：")
                        # issue_type = st.selectbox("问题类型：", ["工时数有误", "遗漏天数未录入", "工作项目与实际不符", "其他"])
                        feedback_text = st.text_area("Please provide a detailed explanation:", placeholder="For example: On July 15th, I actually worked 8.5 hours at the mine, but the table only shows 6 hours...")
                        
                        submit_btn = st.form_submit_button(label="Submit")
                        
                        if submit_btn:
                            if not feedback_text.strip():
                                st.warning("Please fill in the specific feedback instructions.")
                            else:
                                st.success("✅ Feedback submitted successfully! Administrators will review and correct your work hours promptly.")
                                # 提示：生产环境中可将此反馈记录写入数据库或发送通知
        else:
            st.info("👈 Please enter your **employee ID** in the left sidebar to view your work hour details.")
