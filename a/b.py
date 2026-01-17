import re
import os

# 配置
UPSTREAM_DATA_DIR = "upstream_repo/data"
OUTPUT_DIR = "txt"
TASK_CONFIG = "a/tasks.txt"

class RuleConverter:
    def __init__(self, exclude_includes=None):
        self.processed_files = set()
        self.exclude_includes = exclude_includes or []
        # 使用 set 保证去重
        self.rules = {
            "DOMAIN": set(),
            "DOMAIN-SUFFIX": set(),
            "URL-REGEX": set(),
            "DOMAIN-KEYWORD": set()
        }
        self.header_comments = set()
        self.tasks = []

    def read_tasks(self, file_path):
        """
        读取指定格式的txt文件。
        格式: source, exclude1, exclude2...
        """
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    clean_line = line.strip()
                    if not clean_line or clean_line.startswith('#'):
                        continue
                    parts = [p.strip() for p in clean_line.split(',')]
                    source = parts[0]
                    excludes = parts[1:]
                    self.tasks.append((source, excludes))
        except Exception as e:
            print(f"读取任务文件时发生错误: {e}")

    def load_local_file(self, filename):
        """从本地同步的仓库目录读取文件内容"""
        path = os.path.join(UPSTREAM_DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"错误: 找不到文件 {path}")
            return ""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取文件 {filename} 时发生错误: {e}")
            return ""

    def process_line(self, line):
        raw_line = line.strip()
        
        # 1. 处理空行
        if not raw_line:
            return

        # 2. 处理单行注释（保留在 header_comments）
        if raw_line.startswith("#"):
            self.header_comments.add(raw_line)
            return

        # 3. 处理规则后的行内注释
        if "#" in raw_line:
            line_content = raw_line.split("#")[0].strip()
        else:
            line_content = raw_line

        if not line_content:
            return

        # 4. 移除属性 @...
        line_content = re.sub(r'\s*@\S+', '', line_content).strip()

        # 5. 处理包含 include:
        if line_content.startswith("include:"):
            include_file = line_content.split(":", 1)[1].strip()
            # 如果在排除列表中，跳过
            if include_file in self.exclude_includes:
                print(f"  跳过排除的包含文件: {include_file}")
                return
            self.convert(include_file)
            return

        # 6. 转换逻辑
        if line_content.startswith("full:"):
            domain = line_content.split(":", 1)[1].strip()
            self.rules["DOMAIN"].add(f"DOMAIN,{domain}")
        elif line_content.startswith("keyword:"):
            keyword = line_content.split(":", 1)[1].strip()
            self.rules["DOMAIN-KEYWORD"].add(f"DOMAIN-KEYWORD,{keyword}")
        elif line_content.startswith("regexp:"):
            regex = line_content.split(":", 1)[1].strip()
            self.rules["URL-REGEX"].add(f"URL-REGEX,{regex}")
        else:
            # 默认处理为 DOMAIN-SUFFIX
            domain = line_content
            if line_content.startswith("domain:"):
                domain = line_content.split(":", 1)[1].strip()
            self.rules["DOMAIN-SUFFIX"].add(f"DOMAIN-SUFFIX,{domain}")

    def convert(self, filename):
        if filename in self.processed_files:
            return
        self.processed_files.add(filename)
        
        content = self.load_local_file(filename)
        if not content:
            return
            
        for line in content.splitlines():
            self.process_line(line)

    def save_to_file(self, output_name):
        order = ["DOMAIN", "DOMAIN-SUFFIX", "URL-REGEX", "DOMAIN-KEYWORD"]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_name), exist_ok=True)
        
        with open(output_name, "w", encoding="utf-8") as f:
            # 写入单行注释
            if self.header_comments:
                for comment in sorted(list(self.header_comments)):
                    f.write(f"{comment}\n")
            
            # 按顺序写入规则
            for category in order:
                sorted_rules = sorted(list(self.rules[category]))
                for rule in sorted_rules:
                    f.write(f"{rule}\n")

def main():   
    # 1. 尝试从配置文件读取任务
    temp_converter = RuleConverter()
    temp_converter.read_tasks(TASK_CONFIG)
    tasks = temp_converter.tasks

    # 2. 如果配置文件不存在或没有任务，则处理整个 data 目录
    if not tasks:
        if os.path.exists(UPSTREAM_DATA_DIR):
            print(f"未找到任务配置文件或任务为空，将处理目录 {UPSTREAM_DATA_DIR} 下的所有文件...")
            for filename in os.listdir(UPSTREAM_DATA_DIR):
                full_path = os.path.join(UPSTREAM_DATA_DIR, filename)
                if os.path.isfile(full_path):
                    tasks.append((filename, []))
        else:
            print(f"错误: 找不到上游数据目录 {UPSTREAM_DATA_DIR}")
            return

    # 3. 运行转换任务
    for source, excludes in tasks:
        print(f"\n--- 正在处理任务: {source} ---")
        converter = RuleConverter(exclude_includes=excludes)
        converter.convert(source)
        
        # 生成输出路径，处理特殊字符 ! -> not-
        safe_name = source.replace('!', 'not-')
        output_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
        
        converter.save_to_file(output_path)
        print(f"已完成: {source} -> {output_path}")

if __name__ == "__main__":
    main()
