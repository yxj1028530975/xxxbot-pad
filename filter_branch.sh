#!/bin/bash

# 显示将要执行的操作
echo "将执行git filter-branch命令来修改提交历史中的邮箱..."
echo "旧邮箱: 18113565560@163.com"
echo "新邮箱: xxxlaoxia@163.com"

# 询问用户确认
read -p "是否继续？(y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "操作已取消。"
    exit 0
fi

# 执行git filter-branch命令
echo "正在执行命令..."
git filter-branch --env-filter '
    if [ "$GIT_AUTHOR_EMAIL" = "18113565560@163.com" ]
    then
        export GIT_AUTHOR_EMAIL="xxxlaoxia@163.com"
        export GIT_COMMITTER_EMAIL="xxxlaoxia@163.com"
    fi
' --tag-name-filter cat -- --all

echo "操作完成！"
echo "注意：如果这是一个已经推送到远程的仓库，您需要使用 git push --force 来更新远程仓库。"
